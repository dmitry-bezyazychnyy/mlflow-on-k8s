from cmath import log
import os
import sys
import warnings
import logging as logger

import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from sklearn.linear_model import ElasticNet
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


def eval_metrics(actual, pred):
    rmse = np.sqrt(mean_squared_error(actual, pred))
    mae = mean_absolute_error(actual, pred)
    r2 = r2_score(actual, pred)
    return rmse, mae, r2


if __name__ == "__main__":
    np.random.seed(40)
    warnings.filterwarnings("ignore")
    logger.basicConfig(level=logger.INFO)
    
    # Read the wine-quality csv file (make sure you're running this from the root of MLflow!)
    wine_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "wine-quality.csv"
    )
    data = pd.read_csv(wine_path)

    # Split the data into training and test sets. (0.75, 0.25) split.
    train, test = train_test_split(data)

    # The predicted column is "quality" which is a scalar from [3, 9]
    train_x = train.drop(["quality"], axis=1)
    test_x = test.drop(["quality"], axis=1)
    train_y = train[["quality"]]
    test_y = test[["quality"]]

    alpha = float(sys.argv[1]) if len(sys.argv) > 1 else 0.5
    l1_ratio = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5

    with mlflow.start_run() as run:
        # log params
        mlflow.log_param("alpha", alpha)
        mlflow.log_param("l1_ratio", l1_ratio)

        # train model
        lr = ElasticNet(alpha=alpha, l1_ratio=l1_ratio, random_state=42)
        lr.fit(train_x, train_y)

        # eval model
        predicted_qualities = lr.predict(test_x)
        (rmse, mae, r2) = eval_metrics(test_y, predicted_qualities)

        logger.info(f"""
            RMSA: {rmse}
            MAE:  {mae}
            R2:   {r2}
        """)

        # log metrics
        mlflow.log_metric("rmse", rmse)
        mlflow.log_metric("r2", r2)
        mlflow.log_metric("mae", mae)

        # log model (as artifacts)
        mlflow.sklearn.log_model(lr, "model")

        # register in model registry
        model_uri = "runs:/{}/sklearn-model".format(run.info.run_id)
        mv = mlflow.register_model(model_uri, "ElasticNetModel_v1")
        logger.info(f"model: {mv.name}, version: {mv.version}")
        
