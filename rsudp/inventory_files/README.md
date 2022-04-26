# Important
- you need to change all occurrencies of R6833 with your shake's ID

# How to gather the inventory file

- Change the station number before running!

    curl "https://fdsnws.raspberryshakedata.com/fdsnws/station/1/query?network=AM&station=R6833&level=resp&nodata=404&format=xml" > R6833_response.xml