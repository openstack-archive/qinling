const process = require('process')
const express = require('express')
const bodyParser = require('body-parser')
const morgan = require('morgan')
const rp = require("request-promise")

const app = express()
app.use(morgan('combined'))
app.use(bodyParser.urlencoded({ extended: false }))
app.use(bodyParser.json())

function execute(req, res) {
    var executionID = req.body.execution_id
    var functionID = req.body.function_id
    var entry = req.body.entry
    var downloadURL = req.body.download_url
    var token = req.body.token
    var input = req.body.input
    var moduleName
    var handlerName

    if (entry) {
        [moduleName, handlerName] = entry.split('.')
    } else {
        moduleName = 'main'
        handlerName = 'main'
    }

    var modulePath = '/var/qinling/packages/' + functionID + '/' + moduleName
    var userModule
    var userHandler
    var context = {}

    var requestData = {
        'download_url': downloadURL,
        'function_id': functionID,
        'unzip': true
    }
    if (token) {
       requestData['token'] = token
    }

    // download function package and unzip
    async function download(reqBody) {
        let options = {
            uri: 'http://localhost:9091/download',
            method: 'POST',
            headers: {
                "content-type": "application/json",
            },
            body: reqBody,
            json: true,
        }
        await rp(options)
        console.log("download done!")
    }

    // get user's defined function object
    function getHandler() {
        userModule = require(modulePath)
        userHandler = userModule[handlerName]
        if (userHandler === undefined) {
           throw "error"
        }
        console.log("getHandler done!")
    }

    // run user's function
    function run() {
        return Promise.resolve(userHandler(context, input))
    }

    function succeed(result) {
        let elapsed = process.hrtime(startTime)
        let body = {
            "output": result,
            "duration": elapsed[0],
            "success": true,
            "logs": ""
        }

        res.status(200).send(body)
    }

    function fail(error) {
        let elapsed = process.hrtime(startTime)
        let body = {
            "output": "Function invocation error",
            "duration": elapsed[0],
            "success": false,
            "logs": ""
        }

        res.status(500).send(body)
    }

    var startTime = process.hrtime()
    download(requestData).then(getHandler).then(run).then(succeed).catch(fail)
}

app.post('/execute', execute)
app.get('/ping', function ping(req, res) {
    res.status(200).send("pong")
})
app.listen(9090)
