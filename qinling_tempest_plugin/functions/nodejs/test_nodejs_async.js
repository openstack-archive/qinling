var rp = require('request-promise');

exports.main = async function (context, input) {
    var options = {
        uri: 'https://httpbin.org/post',
        method: 'POST',
        body: {
            name: input.name
        },
        json: true,
    };
    return rp(options)
}
