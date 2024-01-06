# MetaML Integration preparation
The MetaML platform's services are provided by a collection of nodes within a P2P network. Any communication to, from and within happens by exchanging 'messages' between nodes or between node and client.
And in order to retrive the bots, as the client of Meyers, you shall provide the context, regime and number of bots 
to the MetaML platform. Please note that, how to connect with MetaML through p2p is provided in the Readme in /healthcare_robothon folder. And below,
there's only instruction on providing the input message towards MetaML(context and regime)



## File Structure and Use

| Folder/File              | Description                                                                                                                                |
|--------------------------|--------------------------------------------------------------------------------------------------------------------------------------------|
| context_transfer.py      | This file will receive the input of raw English context, and scan through the MetaML db and return the contexts in string of numbers       |
| data/Get_regime.py       | This file will extract the key features time-series data and parse it into the form of regime matrix                                       |
| data/regime_generator.py | This file will generator .csv file ready to be used as the regime input to MetaML                                                          |
| AddmetaML.py             | A hub parse the bots requests, send bots request and receive and parse the response message. Store MetaML bots ready for competiton Stage. |




### To Run the Test Process 
### The user just need to provide the MetaML with context and regime
For the context:
Clients can just change the context here in English inside AddmetaML.py and the string of integer contexts would be automatically parsed:
```
# Input the context
"""Change your request context below this line
================================================"""
raw_context = ['Health', 'HeartRate', 'Stress Detection', 'ASD Research', 'Meyer']
print("Input Context (" + ','.join(raw_context) + ")")
"""=============================================
Change your request context above this line"""
```
For the regime: There is a provided regime called Meyers-fingerprint.csv. If clients would like to change the regime, clients can provide the updated time series data and then run the regime_generator.py.
```
 python .\regime_generator.py --symbol {sym} --action {action}

```