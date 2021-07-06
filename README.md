# ImpfBot

Finding COVID-19 vaccination appointments in Germany for https://www.corona-impftermine.net/

![](https://d33wubrfki0l68.cloudfront.net/1d37f117dcdc6c37dbddba2828cf74d487f3d1be/cd1bb/images/header_new.png)

This Python project implements various crawlers to automatically fetch free vaccination appointments and sends them to the users in the Telegram groups. The currently implemented platforms are:

- Doctolib
- Jameda
- Helios Clinics
- MVZ Dachau Verbund
- Samedi
- Zollsoft

In the tools folder, the following additional scripts exist:

- Randstad API / Impf-Finder (currently not used because of low number of appointments)
- Doctolib Puller (allows to find all practices from Doctolib in a specific geolocation)
- Doctolib JSON (downloads json files for those found practices so traffic over the proxy is decreased)

For some cities like Munich, the lists have been split so one roundtrip does not take more than 60 seconds. The servers are currently hosted in Heroku. 

The live statistics for the bots can be found [here](http://corona-impftermine-stats.herokuapp.com/public/dashboard/ec3f6ace-828d-4653-934f-e11b23cc2ff2). The remaining information is on the [website](https://www.corona-impftermine.net/) or in the Telegram groups for the specific city. If you want to get in touch with me, contact me over my [personal website](https://maxritter.net/).
