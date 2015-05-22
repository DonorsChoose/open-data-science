# this function is called from within the Python script ('inventory_forecast.py')
# remove trend, remove seasonality, and forecast

suppressMessages(require(forecast))

forecast_vec = function(vec, log_vec = TRUE, forecast_units = 365) {

  # need to make sure its a vector of integers, especially when passing from Python to R
  vec = as.integer(vec)

  # log
  if (log_vec == TRUE) {
    vec = log(vec)
  }

  # de-trend
  detrend_model = lm(vec ~ c(1:NROW(vec)))
  detrend_int = detrend_model$coefficients[1]
  detrend_slope = detrend_model$coefficients[2]
  for (i in c(1:NROW(vec))) {
    vec[i] = vec[i] - (i * detrend_slope)
  }
  vec = vec - detrend_int

  # de-season
  vec = ts(vec, frequency = 365)
  vec_stl = stl(vec, s.window = 'periodic')
  vec = vec - vec_stl$time.series[,1]

  # save the seasonal pattern
  seasonal_pattern = vec_stl$time.series[,1][1:365]

  # fit residuals using default exponential smoothing method
  vec_forecast = forecast(vec, h = forecast_units)$mean
  vec = c(vec, vec_forecast)

  # add back seasonality
  for (i in c(1:NROW(vec))) {
    if ((i %% 365) == 0) {
      day = 365
    } else {
      day = i %% 365
    }
    vec[i] = vec[i] + seasonal_pattern[day]
  }

  # add back trend
  for (i in c(1:NROW(vec))) {
    vec[i] = vec[i] + (i * detrend_slope)
  }
  vec = vec + detrend_int

  # exponentiate
  if (log_vec == TRUE) {
    vec = exp(vec)
  }

  return(vec)

}