from flask import Flask, jsonify, request

app = Flask(__name__)

nodes = set()


@app.route(rule='/nodes',
           methods=['PUT', 'GET'])
def find_nodes():
    if request.method == 'GET':
        return jsonify(list(nodes))
    elif request.method == 'PUT':
        json_data = request.json
        try:
            if json_data['hosts']:
                for host in json_data['hosts']:
                    nodes.add(host)
        except KeyError:
            return 'Request body format: {"hosts":["ip0:dht_port0", "ip1:dht_port1", ...]}', 400
        return jsonify('ACCEPTED')


if __name__ == '__main__':
    app.run(debug=True, port=5000)
