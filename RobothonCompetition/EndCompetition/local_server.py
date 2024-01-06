from flask import Flask, request, send_file, jsonify
import json
import pandas as pd
import os

app = Flask(__name__)

@app.route('/api/add_fingerprint', methods=['POST'])
def upload():
    # regime_data_file = request.files['datafile']
    # regime_data_file.save(regime_data_file.filename)

    # Comment out
    zip_file = request.files['zipfile']
    zip_file.save(zip_file.filename)

    # print()
    # print('Saved regime data to', regime_data_file.filename)
    # print()

    # aggregates = json.loads(request.form['args'])['aggregates']
    bot_fingerprint = request.form['fingerprint']
    # datafileinfo = json.loads(request.form['args'])['datafileinfo']
    # print('Competition aggregates: ')
    # print(json.dumps(aggregates, indent=4))
    # print()

    print('Bot fingerprint: ')
    print(json.dumps(bot_fingerprint, indent=4))
    print()

    # print('Datafileinfo: ')
    # print(json.dumps(datafileinfo, indent=4))
    # print()

    return "Received data successfully"


@app.route('/api/predict_bots', methods=['POST'])
def upload1():
    print('Im here inside the endpoint')
    # print(json.loads(request.form['fingerprint']))
    # test_regime_data_file = request.files['datafile']
    # test_regime_data_file.save(test_regime_data_file.filename)

    # print()
    # print('Saved test regime data to', test_regime_data_file.filename)
    # print()

    # filters = json.loads(request.form['args'])['filters']
    num_bots = request.form['num_bots']
    print(f'Number of bots: {num_bots}')
    print()
    # datafileinfo = json.loads(request.form['fingerprint'])

    # print('Filters: ')
    # print(json.dumps(filters, indent=4))
    # print()

    print(f'Number of bots: {num_bots}')
    print()

    # print('Datafileinfo: ')
    # print(json.dumps(datafileinfo, indent=4))
    # print()

    ## Similarity search, filtering, etc to find bots

    # bots = {
    #     'bot1.py': '/robothon/vp2359/RobothonHealthcare/HCSimTrading/WinningBotsRepo/0/bot_scripts.zip'
    # }
    # return jsonify(bots)

    return send_file('archive_name.zip', as_attachment=True, download_name='bot_scripts.zip')



if __name__ == '__main__':
    app.run(debug=True)