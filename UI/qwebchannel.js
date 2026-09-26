/****************************************************************************
**
** Copyright (C) 2016 The Qt Company Ltd.
** Copyright (C) 2016 Klarälvdalens Datakonsult AB, a KDAB Group company.
** Contact: https://www.qt.io/licensing/
**
** This file is part of the QtWebChannel module of the Qt Toolkit.
**
** $QT_BEGIN_LICENSE:BSD$
** Commercial License Usage
** Licensees holding valid commercial Qt licenses may use this file in
** accordance with the commercial license agreement provided with the
** Software or, alternatively, in accordance with the terms contained in
** a written agreement between you and The Qt Company. For licensing terms
** and conditions see https://www.qt.io/terms-conditions. For further
** information use the contact form at https://www.qt.io/contact-us.
**
** BSD License Usage
** Alternatively, this file may be used under the terms of the BSD license.
** $QT_END_LICENSE$
**
****************************************************************************/

"use strict";

var QWebChannelMessageTypes = {
    signal: 1,
    propertyUpdate: 2,
    init: 3,
    idle: 4,
    debug: 5,
    invokeMethod: 6,
    connectToSignal: 7,
    disconnectFromSignal: 8,
    setProperty: 9,
    response: 10
};

var QWebChannel = function(transport, initCallback) {
    if (typeof transport !== "object" || typeof transport.send !== "function") {
        console.error("The QWebChannel transport object must have a send() function.");
        return;
    }

    var channel = this;
    this.transport = transport;

    this.send = function(data) {
        if (typeof data !== "string") {
            data = JSON.stringify(data);
        }
        channel.transport.send(data);
    };

    this.transport.onmessage = function(message) {
        var data = message.data;
        if (typeof data === "string") {
            data = JSON.parse(data);
        }
        switch (data.type) {
            case QWebChannelMessageTypes.signal:
                channel.handleSignal(data);
                break;
            case QWebChannelMessageTypes.response:
                channel.handleResponse(data);
                break;
            case QWebChannelMessageTypes.propertyUpdate:
                channel.handlePropertyUpdate(data);
                break;
            default:
                console.error("Invalid message type received: ", data.type);
                break;
        }
    };

    this.execCallbacks = {};
    this.execId = 0;
    this.exec = function(data, callback) {
        if (!callback) {
            channel.send(data);
            return;
        }
        if (channel.execId === Number.MAX_VALUE) {
            channel.execId = Number.MIN_VALUE;
        }
        if (data.hasOwnProperty("id")) {
            console.error("Cannot exec data with pre-existing id: " + JSON.stringify(data));
            return;
        }
        var id = channel.execId++;
        channel.execCallbacks[id] = callback;
        data.id = id;
        channel.send(data);
    };

    this.objects = {};

    this.handleSignal = function(message) {
        var object = channel.objects[message.object];
        if (object) {
            object.signalEmitted(message.signal, message.args);
        } else {
            console.warn("Unhandled signal: " + message.object + "::" + message.signal);
        }
    };

    this.handleResponse = function(message) {
        if (!message.hasOwnProperty("id")) {
            console.error("Invalid response message received: ", JSON.stringify(message));
            return;
        }
        var callback = channel.execCallbacks[message.id];
        delete channel.execCallbacks[message.id];
        if (callback) {
            callback(message.data);
        }
    };

    this.handlePropertyUpdate = function(message) {
        for (var i in message.data) {
            var data = message.data[i];
            var object = channel.objects[data.object];
            if (object) {
                object.propertyUpdate(data.signals, data.properties);
            } else {
                console.warn("Unhandled property update: " + data.object);
            }
        }
        channel.exec({ type: QWebChannelMessageTypes.idle });
    };

    this.debug = function(message) {
        channel.send({ type: QWebChannelMessageTypes.debug, data: message });
    };

    channel.exec({ type: QWebChannelMessageTypes.init }, function(data) {
        for (var objectName in data) {
            var object = new QObject(objectName, data[objectName], channel);
        }
        for (var objName in channel.objects) {
            channel.objects[objName].unwrapProperties();
        }
        if (initCallback) {
            initCallback(channel);
        }
        channel.exec({ type: QWebChannelMessageTypes.idle });
    });
};

function QObject(name, data, webChannel) {
    this.__id__ = name;
    this.__objectSignals__ = {};
    this.__propertyCache__ = {};

    var object = this;
    webChannel.objects[name] = this;

    // Methods
    data.methods.forEach(function(method) {
        var methodName = method[0];
        var methodId = method[1];
        object[methodName] = function() {
            var args = [];
            var callback;
            for (var i = 0; i < arguments.length; ++i) {
                if (typeof arguments[i] === "function") {
                    callback = arguments[i];
                    break;
                }
                args.push(arguments[i]);
            }

            return webChannel.exec({
                type: QWebChannelMessageTypes.invokeMethod,
                object: object.__id__,
                method: methodId,
                args: args
            }, callback);
        };
    });

    // Signals
    data.signals.forEach(function(signal) {
        var signalName = signal[0];
        var signalIndex = signal[1];
        object[signalName] = {
            connect: function(callback) {
                if (typeof callback !== "function") {
                    console.error("Bad callback given to connect to signal " + signalName);
                    return;
                }
                object.__objectSignals__[signalIndex] = object.__objectSignals__[signalIndex] || [];
                object.__objectSignals__[signalIndex].push(callback);
                if (!object.__objectSignals__[signalIndex].connected) {
                    webChannel.exec({
                        type: QWebChannelMessageTypes.connectToSignal,
                        object: object.__id__,
                        signal: signalIndex
                    });
                    object.__objectSignals__[signalIndex].connected = true;
                }
            },
            disconnect: function(callback) {
                if (typeof callback !== "function") {
                    console.error("Bad callback given to disconnect from signal " + signalName);
                    return;
                }
                var connections = object.__objectSignals__[signalIndex];
                if (!connections) return;
                var idx = connections.indexOf(callback);
                if (idx !== -1) {
                    connections.splice(idx, 1);
                    if (connections.length === 0) {
                        webChannel.exec({
                            type: QWebChannelMessageTypes.disconnectFromSignal,
                            object: object.__id__,
                            signal: signalIndex
                        });
                        object.__objectSignals__[signalIndex].connected = false;
                    }
                }
            }
        };
    });

    // Properties
    for (var propertyIndex in data.properties) {
        var property = data.properties[propertyIndex];
        var propertyName = property[0];
        var propertyValue = property[1];
        var notifySignal = property[2];
        object.__propertyCache__[propertyIndex] = propertyValue;

        /* jshint loopfunc: true */
        (function(propIndex, propName, notifySig) {
            var getter = function() {
                return object.__propertyCache__[propIndex];
            };
            var setter = function(value) {
                if (value === undefined) {
                    console.error("Cannot set property " + propName + " to undefined");
                    return;
                }
                object.__propertyCache__[propIndex] = value;
                webChannel.exec({
                    type: QWebChannelMessageTypes.setProperty,
                    object: object.__id__,
                    property: propIndex,
                    value: value
                });
            };
            Object.defineProperty(object, propName, {
                configurable: true,
                get: getter,
                set: setter
            });
        })(propertyIndex, propertyName, notifySignal);
    }
}

QObject.prototype.unwrapProperties = function() {
    for (var propertyIndex in this.__propertyCache__) {
        var value = this.__propertyCache__[propertyIndex];
        this.__propertyCache__[propertyIndex] = this.unwrapQObject(value);
    }
};

QObject.prototype.unwrapQObject = function(response) {
    if (response instanceof Array) {
        for (var i = 0; i < response.length; ++i) {
            response[i] = this.unwrapQObject(response[i]);
        }
        return response;
    }
    if (response && response["__QObject*__"]) {
        return this.webChannel.objects[response["__QObject*__"]];
    }
    return response;
};

QObject.prototype.propertyUpdate = function(signals, propertyMap) {
    for (var propertyIndex in propertyMap) {
        var propertyValue = propertyMap[propertyIndex];
        this.__propertyCache__[propertyIndex] = propertyValue;
    }
    for (var signalName in signals) {
        var args = signals[signalName];
        this.signalEmitted(signalName, args);
    }
};

QObject.prototype.signalEmitted = function(signalIndex, args) {
    var connections = this.__objectSignals__[signalIndex];
    if (connections) {
        for (var i = 0; i < connections.length; ++i) {
            connections[i].apply(this, args);
        }
    }
};