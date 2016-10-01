#!/Users/teraki/Documents/curr-trad/venv/bin/python2.7
import math
import re
import csv
from flask import Flask, jsonify, abort, make_response, request, redirect, url_for


app = Flask(__name__)

def download():
    graph = {}
    currencies = {}

    with open('currencies.csv') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=',')
        d = {}
        for row in reader:
                curr = row.values()[0]
                d[curr] = {i:row[i] for i in row if i!=''}

        for key, value in d.iteritems():
            currencies[key] = {k: float(v) for k, v in value.iteritems()}

    jsrates = {}

    for key, value in currencies.iteritems():
        for curr, rate in value.iteritems():
            jsrates['{}_{}'.format(key, curr)] = str(rate)

    pattern = re.compile("([A-Z]{3})_([A-Z]{3})")
    for key in jsrates:
        matches = pattern.match(key)
        conversion_rate = -math.log(float(jsrates[key]))
        from_rate = matches.group(1).encode('ascii', 'ignore')
        to_rate = matches.group(2).encode('ascii', 'ignore')
        if from_rate != to_rate:
            if from_rate not in graph:
                graph[from_rate] = {}
            graph[from_rate][to_rate] = float(conversion_rate)

    return currencies, graph


def initialize(graph, source):
    d = {}
    p = {}
    for node in graph:
        d[node] = float('Inf')
        p[node] = None
    d[source] = 0
    return d, p


def relax(node, neighbour, graph, d, p):
    if d[neighbour] > d[node] + graph[node][neighbour]:
        d[neighbour] = d[node] + graph[node][neighbour]
        p[neighbour] = node

def retrace_negative_loop(p, start):
    arbitrageLoop = [start]
    next_node = start
    while True:
        next_node = p[next_node]
        if next_node not in arbitrageLoop:
            arbitrageLoop.append(next_node)
        else:
            arbitrageLoop.append(next_node)
            arbitrageLoop = arbitrageLoop[arbitrageLoop.index(next_node):]
            return arbitrageLoop

def bellman_ford(graph, source):
    d, p = initialize(graph, source)
    for i in range(len(graph) - 1):
        for u in graph:
            for v in graph[u]:
                relax(u, v, graph, d, p)

    for u in graph:
        for v in graph[u]:
            if d[v] < d[u] + graph[u][v]:
                return (retrace_negative_loop(p, source))
    return None

currencies, graph = download()


@app.route('/currencies', methods=['GET'])
def get_currencies():
    return jsonify(currencies)


@app.route('/currencies/<string:symbol>', methods=['GET'])
def get_currency(symbol):
    if symbol not in currencies:
        abort(404)
    currency_dict = {k:v for k,v in currencies.iteritems() if symbol in k}
    currency = currency_dict[symbol]
    return jsonify(currency)


@app.route('/sequence', methods=['GET'])
def get_sequence():
    paths = []
    sequence = {}
    for key in graph:
        path = bellman_ford(graph, key)
        if path not in paths and not None:
            paths.append(path)
    print paths
    for path in paths:
        if path is None:
            return "no risk-free opportunities exist yielding over 1.00% profit exist"
        else:
            money = 1
            for i, value in enumerate(path):
                if i + 1 < len(path):
                    start = path[i]
                    end = path[i + 1]
                    rate = math.exp(-graph[start][end])
                    money *= rate
            if money <= 1:
                return "no risk-free opportunities exist yielding over 1.00% profit exist"
            sequence["profit_percent"] = round(money, 2)
            sequence["sequence"] = path
    return jsonify(sequence)


@app.route('/currencies/<string:symbol>', methods=['POST'])
def add_currency(symbol):
    if not request.json:
        abort(400)
    if symbol in currencies:
        return redirect(url_for('get_currency', symbol=symbol))
    currencies[symbol] = request.json
    return jsonify(symbol), 201


@app.route('/currencies/<string:symbol>/<string:to>', methods=['PUT'])
def update_currency(symbol, to):
    if not request.json:
        abort(400)
    if symbol not in currencies:
        abort(400)
    if to not in currencies.get(symbol):
        abort(400)
    key = request.json.keys()[0]
    if key != to:
        abort(400)

    currencies[symbol][to] = request.json[key]
    return jsonify(currencies[symbol])


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

if __name__ == '__main__':
    app.run(debug=True)
