import pandas as pd
import numpy as np
import json
import websocket
import time
import threading
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()

app_id = os.getenv("DERIV_APP_ID")
api_token = os.getenv("DERIV_API_TOKEN")

class DerivAPI:
    """
    A wrapper class for Deriv API to fetch market data for VIX pairs
    """
    
    def __init__(self, app_id=1089, api_token="rBA4bhFrX8rIG8y"):
        self.app_id = app_id
        self.api_token = api_token
        self.api_url = f"wss://ws.binaryws.com/websockets/v3?app_id={str(self.app_id)}"
        self.ws = None
        self.active_symbols = None
        
        # Use a more robust initialization sequence
        try:
            # Connect to websocket
            self._connect()
            
            # Authorize with API token
            auth_result = self._authorize()
            if not auth_result:
                raise Exception("Failed to authorize with the API token")
                
            # Get active symbols
            symbols_result = self._get_active_symbols()
            if not symbols_result:
                raise Exception("Failed to retrieve active symbols")
        except Exception as e:
            # Cleanup in case of any errors
            if self.ws:
                try:
                    self.ws.close()
                except:
                    pass
            raise e
    
    def _connect(self, retries=5, delay=10):
        """Connect to Deriv WebSocket API with retry logic"""
        for attempt in range(retries):
            try:
                self.ws = websocket.create_connection(self.api_url)
                print("✅ Connected to WebSocket successfully")
                return
            except Exception as e:
                print(f"❌ Attempt {attempt + 1} failed: {e}")
                if attempt < retries - 1:
                    print(f"🔄 Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    print("❌ All retry attempts failed.")
        raise Exception("Failed to connect to WebSocket after multiple attempts")
    
    def _authorize(self):
        """Authorize with the API token"""
        try:
            request = {
                "authorize": self.api_token
            }
            response = self._send_request(request)
            
            if response and "authorize" in response:
                print("Successfully authorized with Deriv API")
                return True
            elif response and "error" in response:
                error_code = response["error"]["code"]
                error_message = response["error"]["message"]
                print(f"Authorization failed - Error {error_code}: {error_message}")
                raise Exception(f"API Error {error_code}: {error_message}")
            else:
                print("Failed to authorize with Deriv API - Unknown reason")
                return False
        except Exception as e:
            print(f"Error during authorization: {e}")
            raise Exception(f"API Authorization Error: {str(e)}")
    
    def _ensure_connection(self):
        """Ensure the websocket connection is active"""
        try:
            # Check if the connection is active
            if self.ws is None:
                self._connect()
                self._authorize()
                return
                
            # Send a ping to check if connection is still active
            try:
                self.ws.ping()
            except:
                # If connection is broken, reconnect
                self._connect()
                # Re-authorize after reconnection
                self._authorize()
        except Exception as e:
            print(f"Error ensuring connection: {e}")
            # Try to establish a new connection
            self._connect()
            self._authorize()
    
    def _send_request(self, request_data):
        """Send a request to the Deriv API and get the response"""
        try:
            self._ensure_connection()
            if self.ws is None:
                print("Unable to establish WebSocket connection")
                return None
                
            self.ws.send(json.dumps(request_data))
            response = self.ws.recv()
            return json.loads(response)
        except Exception as e:
            print(f"Error sending request: {e}")
            # Attempt to reconnect and retry once
            try:
                self._connect()
                if self.ws is None:
                    print("Unable to reconnect WebSocket")
                    return None
                    
                # Re-authorize
                self._authorize()
                
                # Try the request again
                self.ws.send(json.dumps(request_data))
                response = self.ws.recv()
                return json.loads(response)
            except Exception as retry_e:
                print(f"Failed to recover from error: {retry_e}")
                return None
    
    def _get_active_symbols(self):
        """Get all active symbols from Deriv API"""
        try:
            request = {
                "active_symbols": "brief",
                "product_type": "basic"
            }
            
            response = self._send_request(request)
            
            if response and "active_symbols" in response:
                self.active_symbols = response["active_symbols"]
                print(f"Retrieved {len(self.active_symbols)} active symbols")
                return True
            elif response and "error" in response:
                error_code = response["error"]["code"]
                error_message = response["error"]["message"]
                print(f"Error fetching active symbols - Error {error_code}: {error_message}")
                return False
            else:
                print("Failed to fetch active symbols - Unknown reason")
                return False
        except Exception as e:
            print(f"Exception while fetching active symbols: {e}")
            return False
    
    def get_vix_symbols(self):
        """Get all VIX and Volatility indices available for trading on Deriv"""
        if self.active_symbols is None:
            result = self._get_active_symbols()
            if not result:
                print("Failed to get active symbols during get_vix_symbols call")
                return []
        
        if self.active_symbols:
            # Get ALL tradeable pairs
            all_symbols = [symbol["symbol"] for symbol in self.active_symbols]
            print(f"Total symbols available: {len(all_symbols)}")
            
            # Comprehensive approach to find ALL VIX and volatility indices
            # This includes all Volatility Indices (R_XX), Volatility Indices 10 (1HZ10V), etc.
            vix_symbols = []
            
            # Market category based search for all volatility indices
            for symbol in self.active_symbols:
                # Check the market/submarket for volatility indices
                is_volatility = (
                    # Direct volatility indices
                    "VIX" in symbol["symbol"] or 
                    symbol["symbol"].startswith("R_") or
                    # Other patterns for volatility indices like 1HZ
                    symbol["symbol"].startswith("1HZ") or
                    # Market category check
                    "volatility" in symbol.get("market", "").lower() or
                    "volatility" in symbol.get("submarket", "").lower() or
                    # Additional check for synthetic indexes
                    "synthetic" in symbol.get("market_display_name", "").lower()
                )
                
                if is_volatility and symbol.get("exchange_is_open", 1) == 1:
                    vix_symbols.append(symbol["symbol"])
            
            if vix_symbols:
                print(f"Found {len(vix_symbols)} volatility indices: {vix_symbols}")
                return vix_symbols
            
            # Fallback to standard volatility indices if no symbols found
            default_symbols = ["R_10", "R_25", "R_50", "R_75", "R_100", "R_100E"]
            print("No volatility indices found, using default symbols")
            return default_symbols
        else:
            print("No active symbols available")
            # Return default VIX symbols as a fallback
            return ["R_10", "R_25", "R_50", "R_75", "R_100", "R_100E"]
    
    def get_candles(self, symbol, timeframe='5m', count=100):
        """
        Get OHLC candle data for a specific symbol
        
        Parameters:
        symbol (str): Market symbol (e.g., "R_10", "R_25", "R_50", "R_75", "R_100")
        timeframe (str): Timeframe for candles (e.g., '5m', '1h')
        count (int): Number of candles to retrieve
        
        Returns:
        pd.DataFrame: DataFrame with OHLC data
        """
        # Convert timeframe to seconds
        timeframe_mapping = {
            '1m': 60,
            '5m': 300,
            '15m': 900,
            '30m': 1800,
            '1h': 3600,
            '4h': 14400,
            '1d': 86400
        }
        
        if timeframe not in timeframe_mapping:
            print(f"Invalid timeframe: {timeframe}. Using default 5m.")
            timeframe = '5m'
        
        granularity = timeframe_mapping[timeframe]
        
        # Calculate start time to ensure we get the right number of candles
        end_time = int(datetime.now().timestamp())
        start_time = end_time - (count * granularity)
        
        request = {
            "ticks_history": symbol,
            "adjust_start_time": 1,
            "count": count,
            "end": end_time,
            "start": start_time,
            "style": "candles",
            "granularity": granularity
        }
        
        response = self._send_request(request)
        
        if response and "candles" in response and response["candles"]:
            # Convert to DataFrame
            candles = response["candles"]
            df = pd.DataFrame([{
                'time': candle['epoch'],
                'open': float(candle['open']),
                'high': float(candle['high']),
                'low': float(candle['low']),
                'close': float(candle['close'])
            } for candle in candles])
            
            # Convert epoch time to datetime and set as index
            df['datetime'] = pd.to_datetime(df['time'], unit='s')
            df = df.set_index('datetime')
            
            return df
        else:
            print(f"Failed to fetch candles for {symbol}")
            return pd.DataFrame()
    
    def buy_contract(self, symbol, amount, duration, duration_unit='m', contract_type='CALL'):
        """
        Buy a contract for a specific symbol
        
        Parameters:
        symbol (str): Market symbol (e.g., "R_10", "R_25", "R_50")
        amount (float): The amount to buy for
        duration (int): Duration value
        duration_unit (str): Duration unit ('t' for ticks, 's' for seconds, 'm' for minutes, 'h' for hours, 'd' for days)
        contract_type (str): Type of contract ('CALL' for rise, 'PUT' for fall)
        
        Returns:
        dict: Contract information or None if failed
        """
        try:
            # Validate contract_type
            if contract_type not in ['CALL', 'PUT']:
                print(f"Invalid contract type: {contract_type}. Using CALL.")
                contract_type = 'CALL'
                
            # Prepare the request
            request = {
                "buy": 1,
                "price": amount,
                "parameters": {
                    "amount": amount,
                    "basis": "stake",
                    "contract_type": contract_type,
                    "currency": "USD",
                    "duration": duration,
                    "duration_unit": duration_unit,
                    "symbol": symbol
                }
            }
            
            # Send request
            response = self._send_request(request)
            
            if response and "buy" in response:
                contract_id = response["buy"]["contract_id"]
                transaction_id = response["buy"]["transaction_id"]
                price = response["buy"]["buy_price"]
                payout = response["buy"].get("payout")
                start_time = datetime.now()
                end_time = start_time + timedelta(minutes=duration if duration_unit == 'm' else 0,
                                                hours=duration if duration_unit == 'h' else 0,
                                                seconds=duration if duration_unit == 's' else 0,
                                                days=duration if duration_unit == 'd' else 0)
                
                return {
                    "contract_id": contract_id,
                    "transaction_id": transaction_id,
                    "price": price,
                    "payout": payout,
                    "symbol": symbol,
                    "contract_type": contract_type,
                    "duration": duration,
                    "duration_unit": duration_unit,
                    "start_time": start_time,
                    "end_time": end_time,
                    "status": "open"
                }
            elif response and "error" in response:
                error_code = response["error"]["code"]
                error_message = response["error"]["message"]
                print(f"Error buying contract - Error {error_code}: {error_message}")
                return None
            else:
                print("Failed to buy contract - Unknown reason")
                return None
                
        except Exception as e:
            print(f"Exception while buying contract: {e}")
            return None

    def check_contract(self, contract_id):
        """
        Check the status of a contract
        
        Parameters:
        contract_id (str): Contract ID to check
        
        Returns:
        dict: Contract status information or None if failed
        """
        try:
            request = {
                "proposal_open_contract": 1,
                "contract_id": contract_id
            }
            
            response = self._send_request(request)
            
            if response and "proposal_open_contract" in response:
                contract = response["proposal_open_contract"]
                
                # Check if contract is settled
                is_sold = contract.get("is_sold", 0) == 1
                is_expired = contract.get("is_expired", 0) == 1
                is_valid_to_sell = contract.get("is_valid_to_sell", 0) == 1
                
                current_spot = contract.get("current_spot")
                entry_spot = contract.get("entry_spot")
                buy_price = contract.get("buy_price")
                sell_price = contract.get("sell_price", 0)
                profit = contract.get("profit")
                
                status = "closed" if is_sold or is_expired else "open"
                result = None
                
                if is_sold or is_expired:
                    result = "win" if profit > 0 else "loss"
                
                return {
                    "contract_id": contract_id,
                    "status": status,
                    "current_spot": current_spot,
                    "entry_spot": entry_spot,
                    "buy_price": buy_price,
                    "sell_price": sell_price,
                    "profit": profit,
                    "is_valid_to_sell": is_valid_to_sell,
                    "result": result
                }
            elif response and "error" in response:
                error_code = response["error"]["code"]
                error_message = response["error"]["message"]
                print(f"Error checking contract - Error {error_code}: {error_message}")
                return None
            else:
                print("Failed to check contract - Unknown reason")
                return None
                
        except Exception as e:
            print(f"Exception while checking contract: {e}")
            return None
            
    def sell_contract(self, contract_id):
        """
        Sell a contract before expiry
        
        Parameters:
        contract_id (str): Contract ID to sell
        
        Returns:
        dict: Contract sell information or None if failed
        """
        try:
            request = {
                "sell": contract_id,
                "price": 0
            }
            
            response = self._send_request(request)
            
            if response and "sell" in response:
                sell_info = response["sell"]
                sold_for = sell_info.get("sold_for")
                transaction_id = sell_info.get("transaction_id")
                contract_id = sell_info.get("contract_id")
                
                return {
                    "contract_id": contract_id,
                    "transaction_id": transaction_id,
                    "sold_for": sold_for,
                    "status": "closed",
                    "sell_time": datetime.now()
                }
            elif response and "error" in response:
                error_code = response["error"]["code"]
                error_message = response["error"]["message"]
                print(f"Error selling contract - Error {error_code}: {error_message}")
                return None
            else:
                print("Failed to sell contract - Unknown reason")
                return None
                
        except Exception as e:
            print(f"Exception while selling contract: {e}")
            return None
            
    def close(self):
        """Close the websocket connection"""
        if self.ws:
            self.ws.close()

# Use the default Deriv app_id (1089) and your demo API token
api = DerivAPI(app_id=1089, api_token="jV7HrgX7DnQxsXU")

# Example WebSocket connection
api_url = f"wss://ws.binaryws.com/websockets/v3?app_id=1089"

try:
    ws = websocket.create_connection(api_url)
    print("Connected successfully using the default app ID and demo API token!")
    ws.close()
except Exception as e:
    print(f"Failed to connect: {e}")
