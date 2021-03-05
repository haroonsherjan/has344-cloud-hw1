const axios = require("axios")
const fs = require('fs')
const aws = require('aws-sdk')

let API_KEY = "ZewN8zdKzaZik_nEiM_mbKfVWCw35PPGREWnFHeJf06cwsx2fxCmQXBvVCFlSkQb0wG-yYne-CKFma7j0--Z-wmfEDJegr54CmtG-4trPadjr6DWxIHTrqyhCcg7YHYx"

// REST
let yelpREST = axios.create({
    baseURL: "https://api.yelp.com/v3/",
    headers: {
        Authorization: `Bearer ${API_KEY}`,
        "Content-type": "application/json",
    },
})

let params = {
    "yelp-restaurants": []
}

let cities = ["Manhattan", "Brooklyn", "Los Angeles", "San Francisco", "Austin", "Houston", "Chicago", "Boston", "Portland", "Phoenix", "Sacramento", "New Orleans"]
let terms = ['mexican', 'italian', 'indian', 'chinese', 'japanese', 'french', 'brazilian', 'moroccan', 'korean', 'german', 'african', "pizza"]

aws.config.update({region: 'us-east-1'});
let db = new aws.DynamoDB();

async function yelpScrape() {
    await fs.writeFile("yelpSearch.json", "", () => {
        console.log("end ")
    })
    for (let city = 0; city < cities.length; city++) {
        for (let term = 0; term < terms.length; term++) {
            let params = { RequestItems: {
                    "yelp-restaurants": []
                }
            }
            await yelpREST("/businesses/search", {
                params: {
                    location: cities[city],
                    term: terms[term],
                    limit: 50
                },
            }).then(async ({data}) => {
                let {businesses} = data
                let count = 0;
                for (let b of businesses) {
                    params.RequestItems["yelp-restaurants"].push({
                        PutRequest: {
                            Item: {
                                id: {S: b.id},
                                name: {S: b.name},
                                address: {S: b.location['address1']},
                                city: {S: cities[city]},
                                cuisine: {S: terms[term]},
                                insertedAtTimestamp: {S: Date.now().toString()}
                            }
                        },
                    })
                    if (params.RequestItems["yelp-restaurants"].length >= 25){
                        await fs.appendFile("yelpSearch.json", JSON.stringify(params), () => {
                            console.log("end ")
                        })
                        await db.batchWriteItem(params, function(err, data) {
                            if (err) {
                                console.log("Error", err);
                            } else {
                                console.log("Success", data);
                            }
                        });
                        params = { RequestItems: {
                                "yelp-restaurants": []
                            }}}}})}}}

yelpScrape()