
Use the following command to list out all the required libraries into conda environment

    conda env export > environment.yml

Use the following command to create the conda environment to run the application

    conda env create -f environment.yml

In this code base I am using Alice Blue as my data feed and also to store the results I am using ElasticSearch as my back end database. So for using the same you need to fill the required details in [helper/env_variables.py](helper/env_variables.py)


| Strategy Code | Underlying | Underlying Type | Strategy Name | File Path |
|:----------:|:-------------:|:------:|:------:|:------:|
| 101 | Nifty | Spot | Short Straddle With Leg Level Stop Loss | [Strategy Code](nifty_short_straddle_with_leg_level_sl.py) |
| 102 | Nifty | Spot | Short Straddle With Premium Level Stop Loss | [Strategy Code](nifty_short_straddle_with_premium_level_sl.py) |
| 201 | Bank Nifty | Spot | Short Straddle With Leg Level Stop Loss | [Strategy Code](banknifty_short_straddle_with_leg_level_sl.py) |
| 202 | Bank Nifty | Spot | Short Straddle With Premium Level Stop Loss | [Strategy Code](banknifty_short_straddle_with_premium_level_sl.py) |