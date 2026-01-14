# market_prediction
New stock market predictor
Benchmark different models (LSTM, LSTM + attnetion, XgBoost Forest) 

Plan:
Dataset: Yahoo Finance - Historical stockdata 
Arch: LSTM (with attention maybe)
Logging: WandB - interactive dashboard for tracking runs 
Containerization: Docker - easy automation using docker images
trading platform: Alpaca API

Design:
*Data: ~100 Tickers, for each 10 years of historical data
  *train on last 10 years
  *validate on last 6 months
  *test on last 6–12 months (walk-forward)


-Store data in Postres

-use moudel to preditc best stock prices over duration of time of time 
-Init profolio
-adjust profolio allocation based on new data
