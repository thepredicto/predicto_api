import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import alpaca_trade_api as tradeapi
import math
import time

from predicto_api_wrapper import TradeAction

class AlpacaApiWrapper(object):
    """Alpaca api wrapper for use with Predicto api wrapper"""

    def __init__(self, apiEndpoint, apiKeyId, apiSecretKey):
        self.api = tradeapi.REST(apiKeyId, apiSecretKey, apiEndpoint, api_version='v2') 
        return

    def submit_market_order(self, action, symbol, qty, investmentAmount, startingPrice, targetSellPrice, stopLossPrice, client_order_id):
        """
        Call to submit a market order position to alpaca
        
        Args:
            action: TradeAction.BUY or TradeAction.SELL (for shorting)
            symbol: the ticker to order
            qty: the quantity of shares to order, if quantity is None or 0, entire investment amount will be used
            investmentAmount: the max investment amount, needs to be able to satisfy given qty
            startingPrice: the expected entry price (price might have changed)
            targetSellPrice: the target exit price (used for trade validations)
            stopLossPrice: the stop loss price (used for trade validations)
            client_order_id: a client order id for tracking
        
        Returns:
            Result will be in the form of: (order, newStartingPrice, newTargetPrice, newStopLossPrice, newQuantity) or None if some error occured
            order: is the alpaca order json, will be none if order couldn't go through
            newStartingPrice, newTargetPrice, newStopLossPrice, newQuantity are re-adjusted based on latest price
        """

        # Re-enable to ONLY allow market orders when market is open 
        # clock = self.api.get_clock()
        # if not clock.is_open :
        #     print('Error: submit_market_order only allowed when market is open!')
        #     return None

        # ONLY allow opening new position if we are not holding one currently
        position = self.get_holding_positions(symbol)
        if position is not None:
            print('Error: already holding open position for {0}'.format(symbol))
            return None

        # ONLY allow opening new position if we haven't traded this symbol (bought or sold) in the last 7 hours (same trading day)
        sinceDate = str((datetime.utcnow() - timedelta(hours=7)))
        filledOrders = self.get_filled_orders_for_symbol_since(symbol, sinceDate)
        if filledOrders is not None and len(filledOrders) > 0:
            print('Error: bought or sold this symbol in the last 7 hours - This check exists to avoid Day Trading Pattern flag, feel freee to remove.')
            return None

        # validate prices
        (goAheadWithTrade, newStartingPrice, newTargetPrice, newStopLossPrice, newQuantity) = self.validate_latest_price_and_stoploss(action, symbol, qty, investmentAmount, startingPrice, targetSellPrice, stopLossPrice)
        if not goAheadWithTrade:
            print('Error: validateLatestPriceAndStopLoss failed')
            return None

        # go ahead and submit order
        order = self.api.submit_order(
            side=action.name.lower(),
            symbol=symbol,
            type='market',
            qty=newQuantity,
            time_in_force='gtc',
            client_order_id=client_order_id
        )

        if order is not None:
            print('Success: submit_market_order ID: {0}'.format(order.id))

        return (order, newStartingPrice, newTargetPrice, newStopLossPrice, newQuantity)


    def submit_bracket_order(self, action, symbol, qty, investmentAmount, startingPrice, targetSellPrice, stopLossPrice, client_order_id):
        """
        Call to submit a bracket order position to alpaca
        
        Args:
            action: TradeAction.BUY or TradeAction.SELL (for shorting)
            symbol: the ticker to order
            qty: the quantity of shares to order, if quantity is None or 0, entire investment amount will be used
            investmentAmount: the max investment amount, needs to be able to satisfy given qty
            startingPrice: the expected entry price (price might have changed)
            targetSellPrice: the target exit price (used for trade validations)
            stopLossPrice: the stop loss price (used for trade validations)
            client_order_id: a client order id for tracking
        
        Returns:
            Result will be in the form of: (order, newStartingPrice, newTargetPrice, newStopLossPrice, newQuantity) or None if some error occured
            order: is the alpaca order json, will be none if order couldn't go through
            newStartingPrice, newTargetPrice, newStopLossPrice, newQuantity are re-adjusted based on latest price
        """
        # ONLY allow opening new position if we are not holding one currently
        position = self.get_holding_positions(symbol)
        if position is not None:
            print('Error: already holding open position for {0}'.format(symbol))
            return None

        # ONLY allow opening new position if we haven't traded this symbol (bought or sold) in the last 7 hours (same trading day)
        sinceDate = str((datetime.utcnow() - timedelta(hours=7)))
        filledOrders = self.get_filled_orders_for_symbol_since(symbol, sinceDate)
        if filledOrders is not None and len(filledOrders) > 0:
            print('Error: bought or sold this symbol in the last 7 hours - This check exists to avoid Day Trading Pattern flag, feel freee to remove.')
            return None

        # validate prices
        (goAheadWithTrade, newStartingPrice, newTargetPrice, newStopLossPrice, newQuantity) = self.validate_latest_price_and_stoploss(action, symbol, qty, investmentAmount, startingPrice, targetSellPrice, stopLossPrice)
        if not goAheadWithTrade:
            print('Error: validateLatestPriceAndStopLoss failed')
            return None

        # go ahead and submit order
        order = self.api.submit_order(
            side=action.name.lower(),
            symbol=symbol,
            type='market',
            qty=newQuantity,
            time_in_force='gtc',
            order_class='bracket',
            take_profit={ 
                'limit_price': str(targetSellPrice)
            },
            stop_loss={
                'stop_price': str(stopLossPrice)
            },
            client_order_id=client_order_id
        )

        if order is not None:
            print('Success: submit_bracket_order ID: {0}'.format(order.id))

        return (order, newStartingPrice, newTargetPrice, newStopLossPrice, newQuantity)


    def open_oco_position(self, parentOrderId, symbol, targetSellPrice, stopLossPrice, client_order_id):
        """
        Call to set take-profit / stoploss orders after opening a position with submit_market_order
        If original position was 'buy', then for this we'll pass 'sell' and vice versa
        Passed parentOrderId (alpaca market order id) must exist, and be already filled.
        
        Args:
            parentOrderId: the alpaca order id for the market order we want to hedge
            symbol: the ticker to order
            targetSellPrice: the target exit price (will be used for oco order)
            stopLossPrice: the stop loss price (will be used for oco order)
            client_order_id: a client order id for tracking
        
        Returns:
            The order json returned from alpaca, or None if something went wrong.
        """
        parentOrder = self.api.get_order(parentOrderId)

        # validate parentOrder matches and makes sense
        error = False
        if parentOrder is None:
            print('Error: parent order doesnt exist')
            error = True
        if parentOrder.symbol != symbol:
            print('Error: symbols dont match for oco order')
            error = True
        if int(parentOrder.filled_qty) == 0:
            print('Error: parent ordet not yet filled')
            error = True
        if parentOrder.status != 'filled':
            print('Error: parent order status is not open!')
            error = True

        if error:
            return None

        newSide = 'sell' if parentOrder.side == 'buy' else 'buy'

        # Check and adjust actual quantity based on held position quantity
        openPosition = self.api.get_position(parentOrder.symbol)
        safeguardQty = parentOrder.filled_qty
        openPositionQty = abs(int(openPosition.qty))
        originalOrderQuantity = int(parentOrder.filled_qty)
        if abs(openPositionQty) != originalOrderQuantity:
            print('Warning: abs(int(openPosition.qty)) != int(parentOrder.filled_qty) - INVESTIGATE')
        if abs(openPositionQty) < originalOrderQuantity:
            safeguardQty = str(abs(openPositionQty))

        order = self.api.submit_order(
            side=newSide,
            symbol=parentOrder.symbol,
            type='limit',
            qty=safeguardQty,
            time_in_force='gtc',
            order_class='oco',
            take_profit={ 
                'limit_price': str(targetSellPrice)
            },
            stop_loss={
                'stop_price': str(stopLossPrice)
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
            action: TradeAction.BUY or TradeAction.SELL (for shorting)
            symbol: the ticker to validate
            qty: the quantity of shares to validate, if quantity is None or 0, entire investment amount will be used
            investmentAmount: the max investment amount, needs to be able to satisfy given qty
            startingPrice: the expected entry price (price might have changed)
            targetSellPrice: the target exit price (used for trade validations)
            stopLossPrice: the stop loss price (used for trade validations)
        
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
            print('Wont process: abs(newTargetSellPercent) < abs(stopLossPercent)')
            return (False, newStartingPrice, targetSellPrice, newStopLossPrice, newQuantity)

        # do some extra checks here
        if action == TradeAction.Buy and (newTargetSellPrice <= newStartingPrice or newStopLossPrice >= newStartingPrice):
            raise Exception('newStartingPrice must be between newStopLossPrice and newTargetSellPrice')
        if action == TradeAction.Sell and (newTargetSellPrice >= newStartingPrice or newStopLossPrice <= newStartingPrice):
            raise Exception('newStartingPrice must be between newStopLossPrice and newTargetSellPrice')

        # else go ahead
        print('Expected price: {0}'.format(startingPrice))
        print('Actual   price: {0}'.format(latestPrice))
        print('Original stopLossPrice: {0}'.format(stopLossPrice))
        print('New stopLossPrice     : {0}'.format(newStopLossPrice))

        return (True, newStartingPrice, targetSellPrice, newStopLossPrice, newQuantity)

    def get_holding_positions(self, symbol=None):
        """
        Returns holding positions for given ticker or all holding positions if no ticker given
        
        Args:
            symbol: the ticker to retrieve holding position for. If None, all positions will be retrieved
        
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
            symbol: the ticker to orders for
            since_date: retrieve filled orders since given date (expected format is YYYY-MM-DD)
        
        Returns:
            A list of orders.
        """
        orders = self.api.list_orders(status='closed', after=since_date, direction='desc', limit=500)

        return [x for x in orders if x.symbol == symbol and x.status == 'filled']

    def get_latest_price(self, symbol):
        """
        Gets latest price of given symbol
        
        Args:
            symbol: the ticker to check
        
        Returns:
            The latest price
        """
        barset = self.api.get_barset(symbol, '1Min', limit=5)
        bars = barset[symbol]
        latestPrice = bars[-1].c

        return latestPrice