import os
import itertools
import numpy as np
import pandas as pd
import multiprocessing as mp
import matplotlib.pyplot as plt
from sklearn.metrics import mean_absolute_error as mae
from scipy import stats
import ApiExtract
from Models import Arima, Lstm

def plot_hybrid(trainData, testData, sarima_forecast, lstm_forecast):

    plt.figure()
    plt.title("SARIMA model")
    plt.plot(trainData, color = 'black', label = "Training data")
    plt.plot(testData, color = 'green', label = "Testing data")
    plt.plot(sarima_forecast, 'r:', label = "Prediction")
    plt.legend(loc = 'upper left')
    plt.show()

    resids = testData - sarima_forecast
    stats.probplot(resids, dist="norm", plot=plt)
    plt.title("Normal Q-Q plot for SARIMA residuals")
    plt.show()

    plt.figure()
    plt.title("lstm predicted residuals")
    plt.plot(resids, color='green', label='test residuals')
    plt.plot(lstm_forecast, 'r:', label='predicted residuals')
    plt.legend(loc='upper left')
    plt.show()

    plt.figure()
    plt.title("Hybrid SARIMA/LSTM model")
    plt.plot(trainData, color = 'black', label = "Training data")
    plt.plot(testData, color = 'green', label = "Testing data")
    plt.plot(sarima_forecast + lstm_forecast, 'r:', label = "ARIMA LSTM prediction")
    plt.legend(loc = 'upper left')
    plt.show()

    residuals = testData - sarima_forecast - lstm_forecast
    stats.probplot(np.array([resid[0] for resid in residuals]), dist="norm", plot=plt)
    plt.title("Normal Q-Q plot for hybrid residuals")
    plt.show()


def getForecasts(sarima, optimal_params, test_data):

    horizon = len(test_data.index)
    sarima_forecast = dd.predict()

    train_resids = sarima.resid().reshape(-1,1) #4 jaar 
    test_resids = np.array(test_data - sarima_forecast).reshape(-1,1) #1 jaar
    # plt.figure()
    # plt.plot(train_resids)
    # plt.show()

    lstm_forecast = lstm(optimal_params, train_resids, test_resids, 0)[1]
    lstm_forecast = pd.Series(lstm_forecast, index=test_data.index)

    arima_performance = round(mae(test_data, sarima_forecast), 3)
    lstm_performance = round(mae(test_data, sarima_forecast + lstm_forecast), 3)

    print(f"\nThe mean absolute error goes from {arima_performance} to {lstm_performance} after fitting the arima residuals using LSTM")

    return sarima_forecast, lstm_forecast


def lstm(params, train_resids, test_resids, teller):

    if teller == 0: print("Fitting a hybrid model using the best parameter combination .....")
    else: print(f"Computing performance for parameter combination {teller}")

    [look_back, output_nodes, nb_epoch, batch_size] = [elt for elt in params]
    m = Lstm(train_resids, test_resids, look_back,  output_nodes, nb_epoch, batch_size)
    generator = m.time_series_generator()
    history = m.fit()
    lstm_prediction = m.predict()
    info = list(params) + [m.mse(), m.rmse(), m.mae()]

    return info, lstm_prediction


def gridSearch(residuals):

    m = 52 if (dd.time_series(keyword).index[1].month - dd.time_series(keyword).index[0].month) == 0 else 12

    train_resids = residuals[:len(residuals)-m]
    test_resids = residuals[len(residuals)-m:]

    param_combinations = list(itertools.product(*params_lstm))
    print("number of combinations for grid search:", len(param_combinations))

    pool = mp.Pool(3)
    performance = pool.starmap(lstm, [(combination, train_resids, test_resids, param_combinations.index(combination)+1) for combination in param_combinations])
    performance = [p[0] for p in performance]
    pool.close()

    performance_df = pd.DataFrame(performance, columns = ['look back', 'output nodes', 'epochs', 'batch size', 'MSE', 'MAE', 'RMSE'])
    print(performance_df)

    optimal_params = performance_df.iloc[performance_df.RMSE.argmin(), :4]
    print("The best parameter combination is:\n", optimal_params)
    print("RMSE:", performance_df.iloc[performance_df.RMSE.argmin(),6])

    return np.array(optimal_params).astype(int)


def main():
    
    train_data = dd.time_series(keyword, True)
    test_data = dd.time_series(keyword, False)
    for p in params_lstm[1]: 
        if (len(test_data) % p != 0): sys.exit("The length of the test data is not a multiple of the output nodes")

    sarima = dd.fit(keyword)
    residuals = sarima.resid().reshape(-1,1)

    optimal_params = gridSearch(residuals)
    sarima_forecast, lstm_forecast = getForecasts(sarima, optimal_params, test_data)

    plot_hybrid(train_data, test_data, sarima_forecast, lstm_forecast)

if __name__ == "__main__":

    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '1' 

    start_year = 2016
    end_year = 2021
    country = 'ES'
    keyword = 'jamon'
    params_lstm = [[52], [1], [600, 800, 1000], [104, 208]]

    df = ApiExtract.extract(range(start_year, end_year), country)    
    dd = Arima(df, .8)

    main()
