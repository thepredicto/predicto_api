import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import alpaca_trade_api as tradeapi
import math
import time

from predicto_api_wrapper import TradeAction, TradeOrderType

class AlpacaApiWrapper(object):
    """
    Alpaca api wrapper for use with Predicto api wrapper
    """
    
    _roundingDecimals = 2

    def __init__(self, apiEndpoint, apiKeyId, apiSecretKey):
        self.api = tradeapi.REST(apiKeyId, apiSecretKey, apiEndpoint, api_version='v2') 
        return

    def submit_order(self, trade_order_type, action, symbol, qty, investmentAmount, startingPrice, targetSellPrice, stopLossPrice, client_order_id):
        """
        Call to submit a bracket order position to alpaca
        
        Args:
            trade_order_type : TradeOrderType.Bracket or TradeOrderType.TrailingStop. Bracket will set fixed stop loss and take profit prices. TrailingStop will set a trailing stop price.
            action           : TradeAction.BUY or TradeAction.SELL (for shorting)
            symbol           : the ticker to order
            qty              : the quantity of shares to order, if quantity is None or 0, entire investment amount will be used
            investmentAmount : the max investment amount, needs to be able to satisfy given qty
            startingPrice    : the expected entry price (price might have changed)
            targetSellPrice  : the target exit price (used for trade validations)
            stopLossPrice    : the stop loss price (used for trade validations)
            client_order_id  : a client order id for tracking
        
        Returns:
            Result will be in the form of: (order, newStartingPrice, newTargetPrice, newStopLossPrice, trailing_percent, newQuantity) or None if some error occured
            order: is the alpaca order json, will be none if order couldn't go through
            newStartingPrice, newTargetPrice, newStopLossPrice, newQuantity are re-adjusted based on latest price
            trailing_percent will be None if order is not TradeOrderType.TrailingStop
        """
        # ONLY allow TrailingStop orders when market is open for now, as it consists of 2 different orders
        if trade_order_type == TradeOrderType.TrailingStop:
            clock = self.api.get_clock()
            if not clock.is_open :
                print('Error: TrailingStop order only allowed when market is open for safety!')
                return None

        # ONLY allow opening new position if we are not holding one currently
        position = self.get_holding_positions(symbol)
        if position is not None:
            print('Error: already holding open position for {0}'.format(symbol))
            return None

        # ONLY allow opening new position if we haven't traded this symbol (bought or sold) in the last 7 hours (same trading day)
        sinceDate = str((datetime.utcnow() - timedelta(hours=7)))
        filledOrders = self.get_filled_orders_for_symbol_since(symbol, sinceDate)
        if filledOrders is not None and len(filledOrders) > 0:
            print('Error: bought or sold this symbol in the last 7 hours - This check exists to avoid Day Trading Pattern flag, feel free to remove.')
            return None

        # validate prices
        (goAheadWithTrade, newStartingPrice, newTargetPrice, newStopLossPrice, newQuantity) = self.validate_latest_price_and_stoploss(action, symbol, qty, investmentAmount, startingPrice, targetSellPrice, stopLossPrice)
        if not goAheadWithTrade:
            print('Error: validateLatestPriceAndStopLoss failed')
            return None

        # go ahead and submit asked order
        if trade_order_type == TradeOrderType.Market:
            order = self.api.submit_order(
                side=action.name.lower(),
                symbol=symbol,
                type='market',
                qty=newQuantity,
                time_in_force='gtc',
                client_order_id=client_order_id
            )

        elif trade_order_type == TradeOrderType.Bracket:
            order = self.api.submit_order(
                side=action.name.lower(),
                symbol=symbol,
                type='market',
                qty=newQuantity,
                time_in_force='gtc',
                order_class='bracket',
                take_profit={ 
                    'limit_price': str(round(targetSellPrice, AlpacaApiWrapper._roundingDecimals))
                },
                stop_loss={
                    'stop_price': str(round(newStopLossPrice, AlpacaApiWrapper._roundingDecimals))
                },
                client_order_id=client_order_id
            )
            trailing_percent = None

        elif trade_order_type == TradeOrderType.TrailingStop:
            # calculate trailing stop percent
            trailing_percent = (abs(newStopLossPrice - newStartingPrice) / newStartingPrice) * 100
            # minimum tralinig percent allowed by alpaca is 0.1% 
            trailing_percent = max(trailing_percent, 0.1)

            print('Trailing stop percent  : {0:.2f}%'.format(trailing_percent))

            # submit market order first
            order = self.api.submit_order(
                side=action.name.lower(),
                symbol=symbol,
                type='market',
                qty=newQuantity,
                time_in_force='gtc',
                client_order_id=client_order_id
            )

            # go ahead and submit trailing stop order
            if order is not None:
                trailing_stop_order = None
                # retry here until previous order is filled
                for _ in range(0, 5):
                    trailing_stop_order = self.open_trailing_stop_position(order.id, symbol, trailing_percent, client_order_id + '_trailstop')
                    if trailing_stop_order is not None:
                        break
                    
                    print('Waiting for market order to be filled to set trailing stop loss... will retry in 10 seconds')
                    time.sleep(10)

                if trailing_stop_order is None:
                    print('Market order didnt go through or couldnt set trailing stop. Cancelling...')
                    # cancel order here
                    self.api.cancel_order(order.id)
                    pass

        if order is not None:
            print('Success: submit_order ID: {0}'.format(order.id))

        return (order, newStartingPrice, newTargetPrice, newStopLossPrice, trailing_percent, newQuantity)

    def open_trailing_stop_position(self, parentOrderId, symbol, trailing_stop_percent, client_order_id):
        """
        Call to set trailing stop orders after opening a position
        If original position was 'buy', then for this we'll pass 'sell' and vice versa
        Passed parentOrderId (alpaca market order id) must exist, and be already filled.
        
        Args:
            parentOrderId         : the alpaca order id for the market order we want to hedge
            symbol                : the ticker to order
            trailing_stop_percent : the trailing stop percentage
            client_order_id       : a client order id for tracking
        
        Returns:
            The order json returned from alpaca, or None if something went wrong.
        """
        parentOrder = self.api.get_order(parentOrderId)

        # validate parentOrder matches and makes sense
        ok = self.validate_parent_order_filled_and_match(parentOrder, symbol)

        if not ok:
            return None

        newSide = 'sell' if parentOrder.side == 'buy' else 'buy'

        # Check and adjust actual quantity based on held position quantity
        safeguardQty = self.get_and_validate_quantity_to_hedge(parentOrder)

        order = self.api.submit_order(
            side=newSide,
            symbol=parentOrder.symbol,
            qty=safeguardQty,
            type='trailing_stop',
            trail_percent=trailing_stop_percent,
            time_in_force='gtc',
        )

        if order is not None:
            print('Success: open_trailing_stop_position ID: {0}'.format(order.id))

        return order

    def open_oco_position(self, parentOrderId, symbol, targetSellPrice, stopLossPrice, client_order_id):
        """
        Call to set take-profit / stoploss orders after opening a market order position with submit_order
        If original position was 'buy', then for this we'll pass 'sell' and vice versa
        Passed parentOrderId (alpaca market order id) must exist, and be already filled.
        
        Args:
            parentOrderId   : the alpaca order id for the market order we want to hedge
            symbol          : the ticker to order
            targetSellPrice : the target exit price (will be used for oco order)
            stopLossPrice   : the stop loss price (will be used for oco order)
            client_order_id : a client order id for tracking
        
        Returns:
            The order json returned from alpaca, or None if something went wrong.
        """
        parentOrder = self.api.get_order(parentOrderId)

        # validate parentOrder matches and makes sense
        ok = self.validate_parent_order_filled_and_match(parentOrder, symbol)

        if not ok:
            return None

        newSide = 'sell' if parentOrder.side == 'buy' else 'buy'

        # Check and adjust actual quantity based on held position quantity
        safeguardQty = self.get_and_validate_quantity_to_hedge(parentOrder)

        order = self.api.submit_order(
            side=newSide,
            symbol=parentOrder.symbol,
            type='limit',
            qty=safeguardQty,
            time_in_force='gtc',
            order_class='oco',
            take_profit={ 
                'limit_price': str(round(targetSellPrice, AlpacaApiWrapper._roundingDecimals))
            },
            stop_loss={
                'stop_price': str(round(stopLossPrice, AlpacaApiWrapper._roundingDecimals))
            },
            client_order_id=client_order_id
        )

        if order is not None:
            print('Success: open_oco_position ID: {0}'.format(order.id))

        return order

    def validate_latest_price_and_stoploss(self, action, symbol, qty, investmentAmount, startingPrice, targetSellPrice, stopLossPrice):
        """
        Check startingPrice is what we expect (might have changed since our recommendation was created)
        returns (goAheadWithTrade, newStartingPrice, targetSellPrice, stopLossPrice, newQuantity)
        
        Args:
            action           : TradeAction.BUY or TradeAction.SELL (for shorting)
            symbol           : the ticker to validate
            qty              : the quantity of shares to validate, if quantity is None or 0, entire investment amount will be used
            investmentAmount : the max investment amount, needs to be able to satisfy given qty
            startingPrice    : the expected entry price (price might have changed)
            targetSellPrice  : the target exit price (used for trade validations)
            stopLossPrice    : the stop loss price (used for trade validations)
        
        Returns:
            Result will be in the form of:(goAheadWithTrade, newStartingPrice, targetSellPrice, stopLossPrice, newQuantity)
            goAheadWithTrade: whether given prices make sense and we should go ahead
            newStartingPrice, newQuantity are re-adjusted based on latest price
        """

        # double check things look ok
        if action not in [TradeAction.Buy, TradeAction.Sell]:
            raise Exception('Wrong trade action passed')
        if action == TradeAction.Buy and (targetSellPrice <= startingPrice or stopLossPrice >= startingPrice):
            raise Exception('targetSellPrice must be between stopLossPrice and targetSellPrice')
        if action == TradeAction.Sell and (targetSellPrice >= startingPrice or stopLossPrice <= startingPrice):
            raise Exception('targetSellPrice must be between stopLossPrice and targetSellPrice')

        # get latest price 
        latestPrice = self.get_latest_price(symbol)

        # check if investmentAmount is enough to invest, or calculate qty if not given
        if investmentAmount is None:
            raise Exception('investmentAmount is required')
        if qty is None:
            qty = math.floor(investmentAmount/latestPrice)
            if qty == 0:
                print('Wont process: investmentAmount is less than latest stock Price (${0})'.format(latestPrice))
                return (False, latestPrice, None, None, qty)

        if (qty * latestPrice) > investmentAmount:
            print('Wont process: (qty * latestPrice) > investmentAmount')
            return (False, latestPrice, None, None, qty)

        newQuantity = qty
        newStartingPrice = latestPrice

        # if we already hit our target price, it's too late, cancel order
        if action == TradeAction.Buy and (latestPrice >= targetSellPrice):
            print('Wont process - Price already moved: action == TradeAction.Buy and (latestPrice >= targetSellPrice)')
            return (False, latestPrice, None, None, newQuantity)
        if action == TradeAction.Sell and (latestPrice <= targetSellPrice):
            print('Wont process - Price already moved: action == TradeAction.Sell and (latestPrice <= targetSellPrice)')
            return (False, latestPrice, None, None, newQuantity)
        if action == TradeAction.Noaction:
            print('Wont process: action == TradeAction.Noaction')
            return (False, latestPrice, None, None, newQuantity)

        # otherwise re-adjust StopLossPrice to match original allowed percentage loss
        stopLossPercent = (stopLossPrice - startingPrice) / startingPrice
        newStopLossPrice = newStartingPrice + (newStartingPrice * stopLossPercent)
        # we never re-adjust targetSellPrice for the time being
        newTargetSellPrice = targetSellPrice

        # if new loss risk is more than potential gain, cancel order
        newTargetSellPercent = (targetSellPrice - newStartingPrice) / newStartingPrice
        if abs(newTargetSellPercent) < abs(stopLossPercent):
            print('Wont process, new loss risk is more than potential gain: abs(newTargetSellPercent) < abs(stopLossPercent)')
            return (False, newStartingPrice, targetSellPrice, newStopLossPrice, newQuantity)

        # do some extra checks here
        if action == TradeAction.Buy and (newTargetSellPrice <= newStartingPrice or newStopLossPrice >= newStartingPrice):
            raise Exception('newStartingPrice must be between newStopLossPrice and newTargetSellPrice')
        if action == TradeAction.Sell and (newTargetSellPrice >= newStartingPrice or newStopLossPrice <= newStartingPrice):
            raise Exception('newStartingPrice must be between newStopLossPrice and newTargetSellPrice')

        # else go ahead
        print('Expected price         : {0}'.format(startingPrice))
        print('Actual   price         : {0}'.format(latestPrice))
        print('Original stopLossPrice : {0}'.format(stopLossPrice))
        print('New stopLossPrice      : {0}'.format(newStopLossPrice))
        print('Target Price           : {0}'.format(newTargetSellPrice))

        return (True, newStartingPrice, targetSellPrice, newStopLossPrice, newQuantity)

    def validate_parent_order_filled_and_match(self, parentOrder, symbol):
        """
        Validates that the alpaca parent order matches our symbol and is filled
        
        Args:
            parentOrder : the alpaca parent order to check
            symbol      : the symbol to match
        
        Returns:
            True or False
        """
        ok = True
        if parentOrder is None:
            print('Error: parent order doesnt exist')
            ok = False
        if parentOrder.symbol != symbol:
            print('Error: symbols dont match for oco order')
            ok = False
        if int(parentOrder.filled_qty) == 0:
            print('Error: parent ordet not yet filled')
            ok = False
        if parentOrder.status != 'filled':
            print('Error: parent order status is not open!')
            ok = False

        return ok

    def get_and_validate_quantity_to_hedge(self, parentOrder):
        """
        Validates, adjusts and returns the quantity of shares to hedge based on held position quantity
        
        Args:
            parentOrder : the alpaca parent order to check
        
        Returns:
            The quantity to hedge
        """
        openPosition = self.api.get_position(parentOrder.symbol)
        safeguardQty = parentOrder.filled_qty
        openPositionQty = abs(int(openPosition.qty))
        originalOrderQuantity = int(parentOrder.filled_qty)
        if abs(openPositionQty) != originalOrderQuantity:
            print('Warning: abs(int(openPosition.qty)) != int(parentOrder.filled_qty) - INVESTIGATE')
        if abs(openPositionQty) < originalOrderQuantity:
            safeguardQty = str(abs(openPositionQty))

        return safeguardQty

    def get_holding_positions(self, symbol=None):
        """
        Returns holding positions for given ticker or all holding positions if no ticker given
        
        Args:
            symbol : the ticker to retrieve holding position for. If None, all positions will be retrieved
        
        Returns:
            The position information if symbol is given, or a list of all open positions otherwise
        """
        if symbol is not None:
            # get single position
            try:
                return self.api.get_position(symbol)
            except:
                return None
        else:
            # get all positions
            positions = self.api.list_positions()
            for position in positions:
                print("Holding {} shares of {}".format(position.qty, position.symbol))
            return positions
        
    def get_filled_orders_for_symbol_since(self, symbol, since_date):
        """
        Returns orders for given symbol that were filled since given date 
        
        Args:
            symbol     : the ticker to orders for
            since_date : retrieve filled orders since given date (expected format is YYYY-MM-DD)
        
        Returns:
            A list of orders.
        """
        orders = self.api.list_orders(status='closed', after=since_date, direction='desc', limit=500)

        return [x for x in orders if x.symbol == symbol and x.status == 'filled']

    def get_latest_price(self, symbol):
        """
        Gets latest price of given symbol
        
        Args:
            symbol : the ticker to check
        
        Returns:
            The latest price
        """
        barset = self.api.get_latest_bar(symbol)
        latestPrice = barset.c

        return latestPrice