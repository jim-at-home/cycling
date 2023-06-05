import os
import requests
import json
import sys
import gpxpy
from math import sin, cos, sqrt, atan2, radians

def calculate_distance(lat1, lon1, lat2, lon2):
    # approximate radius of Earth in meters
    R = 6371000

    # convert decimal degrees to radians
    lat1_rad = radians(lat1)
    lon1_rad = radians(lon1)
    lat2_rad = radians(lat2)
    lon2_rad = radians(lon2)

    # haversine formula
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = R * c

    return distance

# hard wire search criteria (Woodbridge) distance is in metres
lat, lon, dist = 52.16344964521758, 0.5069332657261196, 500

# load any existing tcx names into a list from the 'tracks' directory...
files = []
directory = os.getcwd() + "\\tracks"
print ("Loading existing routes...")
for file in os.listdir(directory):
	if os.path.isfile(os.path.join(directory, file)) and file.endswith('.gpx') :
		files.append(file[:file.rfind(".")])

# Now, load the latest routes from RWGPS - public method seems to get latest 25 routes... User 657096 is me!
r = requests.get ("https://ridewithgps.com/users/657096/routes.json" )

#...or call with credentials can take parameters, but need auth token...
#r = requests.get ("https://ridewithgps.com/users/657096/routes.json", params={"offset" : "0", "limit" : "500", "version": "2", "apikey": "testkey1", "auth_token": "1869bd7dd7795934a4b2cb311cd5cd7f" } )

if (r.status_code == 200) :
	routes = json.loads(r.content)
else:
	print(f"Error: {r.status_code} - {r.content}")

# Loop through the routes, and download if we don't have it
print ("Checking for new routes on RWGPS...")
for route in routes:
	id = route['id']
	if (f'{id}' not in files):
		print(f'Route: {id} does not exist - downloading GPX...')
		r = requests.get (f"https://ridewithgps.com/routes/{id}.gpx")
		if (r.status_code == 200):
			with open(f"tracks\\{id}.gpx", "wb") as file:
				file.write(r.content)
		else:
			print(f'Failed to get route {id}: {r.status_code}')

# OK - now we loop through our tracks and look for one that's near our destination...
matched_routes = set() 	# a set to avoid duplicates when adding route matches...
print(f"Now checking for track that's within {dist}m of lat:{lat}, lon:{lon}")
num_tracks = len(os.listdir(directory))
count = 0
for file in os.listdir(directory):
	count += 1
	if os.path.isfile(os.path.join(directory, file)) and file.endswith('.gpx') :
		print(f"Checking files: {file} - {count / num_tracks:.1%}", end="\r")
		with open(os.path.join(directory, file), 'r') as gpx_file:
			gpx = gpxpy.parse(gpx_file)
			for track in gpx.tracks:
				for segment in track.segments:
					for point in segment.points:
						distance = calculate_distance(lat, lon, point.latitude, point.longitude)
						#print (f"lat:{point.latitude}, lon:{point.longitude}, distance:{distance}")
						if distance < dist:
							#print (f"Route {file} matched! - lat:{point.latitude}, lon:{point.longitude}, distance:{distance}")
							matched_routes.add(file[:file.rfind(".")])
			
print (f"Matched tracks: {matched_routes}")
