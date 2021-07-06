
const https = require("https")
const prompt = require('prompt-sync')();
const Distance = require('geo-distance');
const fs = require("fs")

const hostName = 'www.doctolib.de'

function intervals(seconds) {
  return new Promise((resolve) => {
    setInterval(resolve, seconds * 1000)
  });
}

async function request(host, path, method) {
  const options = {
    hostname: host,
    path: path,
    method: method
  }

  let url = `https://${options.hostname + options.path}`
  return new Promise((resolve, reject) => {
    const req = https.request(options, res => {
      if (res.statusCode != 200) {
        console.error(`Invalid code error on url ${url}`)
      }
      let buf = ""
      res.on('data', d => {
        buf += d
      })

      res.on('end', () => {
        return resolve(buf)
      })
    })

    req.on('error', error => {
      return reject(`Request failed '${error}' on url '${url}'`)
    })

    req.end()
  })
}

async function getTotalOfPage(city, domain) {
  let buf = []
  try {
    buf = await request(hostName, `/${domain}/${city}`, 'GET')
    const regex = /search_results_total&quot;:\d+/;
    const found = buf.match(regex)
    if (found === null || found.length == 0) {
      console.error(`[get-total-page] Cannot find any result on '${url}'`)
      return
    }
    const splitArr = found[0].split(":")
    if (!Array.isArray(splitArr) && splitArr.length < 2) {
      console.log(`[get-total-page] Split str failed on '${found}' and url '${url}'`)
      return
    }
    return Math.ceil(splitArr[1] / 10)
  } catch (err) {
    return
  }
}

async function getCenterIDs(pageNumber, city, domain, longitude, latitude, maxDistance) {
  let buf = []
  const mainCity = {
    lat: latitude,
    lon: longitude
  }

  try {
    // Care: special case on first page ...
    // Increment to get the correct page number
    pageNumber++;
    let path = ""
    if (pageNumber == 1) {
      path = `/${domain}/${city}`
    } else {
      path = `/${domain}/${city}?page=${pageNumber}`
    }
    buf = await request(hostName, path, 'GET')
    const regex = /linkProfileName" href="[^?"]*/g
    const found = buf.match(regex)
    if (found === null || found.length == 0) {
      console.error(`[get-center-id] Cannot find any result on '${url}'`)
      return
    }
    const latRegex = /data-lat="[^"]*/g
    const lngRegex = /data-lng="[^"]*/g
    const latResults = buf.match(latRegex)
    const lngResults = buf.match(lngRegex)

    let centerIDs = []
    var counter = 0
    found.forEach(element => {
      const splitArr = element.split('"')
      if (!Array.isArray(splitArr) && splitArr.length < 3) {
        console.log(`[get-center-id] Split str failed on '${element}' and url '${url}'`)
        return
      }
      const splitLat = latResults[counter].split('"')
      const splitLng = lngResults[counter].split('"')
      const compCity = {
        lat: splitLat[1],
        lon: splitLng[1]
      }
      const distanceKm = Distance.between(mainCity, compCity).human_readable()['distance'];
      if ((distanceKm <= maxDistance) || (distanceKm >= 250)) {
        centerIDs.push('https://' + hostName + splitArr[2])
      }
      counter = counter + 1
    });
    return centerIDs
  } catch (err) {
    return
  }
}

function removeDuplicates(arr) {
  o = {}
  arr.forEach(function (e) {
    o[e] = true
  })
  return Object.keys(o)
}

async function startPulling() {
  const city = prompt('What is your city? (f. ex. muenchen): ');
  const abbr = prompt('What should be the abbreviation for your city? ');
  const maxDistance = prompt('What should be the maximum distance in kilometers? (f. ex. 50): ');
  const latitude = prompt('What is the latitude of the city? (f. ex. 48.155004): ');
  const longitude = prompt('What is the longitude of the city? (f. ex. 11.4717963): ');
  const domains = [
    'praxis',
    'einzelpraxis',
    'privatpraxis',
    'praxisgemeinschaft',
    'gemeinschaftspraxis',
    'medizinisches-versorgungszentrum-mvz',
    'krankenhaus',
    'klinik',
    'privatklinik',
    'zahnarztpraxis',
    'institut',
    'med-zentrum-fuer-erwachsene-mit-behinderung-mzeb',
    'testzentrum-covid',
    'zmvz-zahnmedizinisches-versorgungszentrum',
    'radiologie-zentrum',
    'impfung-covid-19-corona',
    'allgemeinmedizin',
    'innere-und-allgemeinmediziner',
    'hausarztliche-versorgung',
    'impfung-impfberatung'
  ]
  var centerURLs = []

  // Go through all domains
  for (let i = 0; i < domains.length; i++) {
    // Get number of pages
    console.log("CURRENT: " + domains[i])
    const pageTotal = await getTotalOfPage(city, domains[i])
    if (pageTotal === null || typeof pageTotal !== "number") {
      console.error("Cannot get number of page")
    }

    // Get center URLs
    for (let j = 0; j < pageTotal; j++) {
      const centerURL = await getCenterIDs(j, city, domains[i], longitude, latitude, maxDistance)
      if (centerURL !== undefined) {
        centerURLs.push(...centerURL)
      }
    }
  }

  //Outprint results
  console.log("-------------------------------------------")
  console.log("")
  const writeStream = fs.createWriteStream('../../data/' + abbr + '.txt')
  centerURLs = removeDuplicates(centerURLs)
  centerURLs.forEach(async (centerURL) => {
    console.log(centerURL)
    writeStream.write(`${centerURL}\n`)
  });
  writeStream.end()
}

startPulling()

