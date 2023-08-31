# %% [markdown]
# ## Functions

# %% [markdown]
# Credits to Patrick who did a folium "Camino's" project which I based the mapping stuff off...
# (https://github.com/datachico/gpx_to_folium_maps/blob/master/folium_maps_From_GPX.ipynb)

# %%
def refresh_rwgps_routes ( directory = 'tracks', user:int = 657096, api_key = '', auth_token = '' ) -> list:
    # Download routes for a given user from RWGPS
    # Downloads into directory ".\tracks" relative to CWD by default, only if the GPX file isn't already there
    # If you have a developer token, this can check many routes, otherwise the public interface seems to load the most recent 25
    # (see https://ridewithgps.com/api)
    if not(os.path.exists(directory)):
        os.mkdir(directory)

    # get list of existing routes
    files = []
    for file in os.listdir(directory):
        if os.path.isfile(os.path.join(directory, file)) and file.endswith('.gpx') :
            files.append(file)
    print (f"Found {len(files)} existing routes in directory '{directory}'...")
    
    # Now, load the latest routes from RWGPS - public method seems to get latest 25 routes... User 657096 is me!
    if api_key == "":
        r = requests.get (f"https://ridewithgps.com/users/{user}/routes.json" )
    else:
        #...or call with credentials can take parameters, but need auth token...
        r = requests.get (f"https://ridewithgps.com/users/{user}/routes.json", params={"offset" : "0", "limit" : "500", "version": "2", "apikey": api_key, "auth_token": auth_token } )

    if (r.status_code == 200) :
        if (api_key == ""):
            routes = json.loads(r.content)
        else:
            # return structure is different in authenticated call!
            routes = json.loads(r.content)['results']
    else:
        print(f"Error: {r.status_code} - {r.content}")
        return []
        
    # Loop through the routes, and download if we don't have it
    print(f"Checking most recent {len(routes)} routes from RWGPS for missing routes")
    for route in routes:
        id = f"{route['id']}.gpx"
        if (id not in files):
            print(f'Route: {id} does not exist - downloading GPX...')
            r = requests.get (f"https://ridewithgps.com/routes/{id}")
            if (r.status_code == 200):
                with open(f"tracks\\{id}", "wb") as file:
                    file.write(r.content)
                files.append( str(id) )
            else:
                print(f'Failed to get route {id}: {r.status_code}')
    
    return files

# %%
def calculate_distance(lat1, lon1, lat2, lon2) -> float:
    # Use Haversine formula to caucluate distance between 2 points in meters
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

# %%
def load_gpx_from_file ( filename:str ) -> dict:
    # load GPX file into dictionary
    # returns dictionary - {link:str, name:str, length:float, uphill:float, midpoint:(lat,lon), points: [(lat,lon),(lat,lon)...]}    with open(filename, 'r') as gpx_file:
    with open(filename, "r") as gpx_file:
        gpx = gpxpy.parse(gpx_file)

    gpx_return = dict(name = gpx.name if not(gpx.name == None) else gpx.tracks[0].name,
                      link = gpx.link if not(gpx.link == None) else "#",
                      length = gpx.length_3d(),
                      uphill = gpx.get_uphill_downhill().uphill,
                      points = [])
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                gpx_return['points'].append((point.latitude, point.longitude))
    num_points = len(gpx_return['points'])
    gpx_return['midpoint'] = gpx_return['points'][num_points//2]
    return gpx_return

# %%
def find_close_routes ( directory:str, lat:float, lon:float, dist:int = 100, max_routes:int = 10 ) -> list:

	matched_routes = {} # empty dictionary for our routes
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
								# we add this file if it doesn't exist, or we need to update its distance
								match_file = matched_routes.get(file, -1)
								if match_file == -1 or matched_routes[file] > distance :
									matched_routes[file] = distance

	#move output onto newline...
	print('')

	if len(matched_routes) > max_routes:
		print(f'Warning: {len(matched_routes)} routes matched criteia - output restricted to the closest {max_routes}')

	# one line, but we sort the matches (yields a list of tuples), take the first 'max_routes' of these and convert back into a dictionary
	matched_routes = dict(sorted(matched_routes.items(),key=lambda x:x[1])[:max_routes])
	# just return the matched filenames (which are the keys of the dictionary) as a list
	return list(matched_routes.keys())

# %%
def make_folium_map( directory:str = './', file_list:list = [], map_path='routes.html', match_point = None, zoom_level=12, marker_text = ''):
    activity_icon='bicycle'
    mymap = None

    # assumes input is list of file roots
    for file in file_list:
        route = load_gpx_from_file ( os.path.join(directory, file))
		
        #print('data created for ' + file)

        #get start and end lat/long
        lat_start, long_start = route['points'][0]
        activity_color = ['red', 'blue', 'green', 'orange', 'purple', 'gray', 'pink'][file_list.index(file)%7]
        
        #first time through, we create the map - after that, we're just adding lines to it...
        if file_list.index(file) == 0:
            mymap = folium.Map( location=[ lat_start, long_start ], zoom_start=zoom_level)
            folium.TileLayer('openstreetmap', name='OpenStreet Map', control=False).add_to(mymap)
            #folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}', attr="Tiles &copy; Esri &mdash; National Geographic, Esri, DeLorme, NAVTEQ, UNEP-WCMC, USGS, NASA, ESA, METI, NRCAN, GEBCO, NOAA, iPC", name='Nat Geo Map').add_to(mymap)
            #folium.TileLayer('http://tile.stamen.com/terrain/{z}/{x}/{y}.jpg', attr="terrain-bcg", name='Terrain Map').add_to(mymap)

            #fullscreen option
            plugins.Fullscreen( position='topright' ).add_to(mymap)


        #put route in a FeatureGroup so we can show/hide it
        fg = folium.FeatureGroup(f"<span style='color: {activity_color};'>{route['name']} ({route['length']/1000:.1f}k)</span>",)
        #add_line
        html_hint = f"""
                    <span style='white-space: nowrap;'>
                    <a href='{route['link']}'>{route['name']}</a><br>
                    Length: {route['length']/1000:.1f}k<br>
                    Climb: {route['uphill']:.0f}m<br>
                    File: {file}
                    </span>
                    """
        fg.add_child(folium.PolyLine(route['points'], popup=folium.Popup(html_hint), color=activity_color, weight=4.5, opacity=.5))
    
        #build starting marker
        fg.add_child(folium.vector_layers.CircleMarker(location=[lat_start, long_start], radius=9, color=activity_color, weight=1, fill_color=activity_color, fill_opacity=1, popup=folium.Popup(html_hint)))
        #Overlay triangle
        fg.add_child(folium.RegularPolygonMarker(location=[lat_start, long_start], fill_color='white', fill_opacity=1, color='white', number_of_sides=3, radius=3, rotation=0, popup=folium.Popup(html_hint)))
    
        fg.add_to(mymap)
        
    if mymap != None :
        if match_point != None :
            #add origin marker to map
            folium.Marker(match_point, tooltip = marker_text, icon=folium.Icon(color='red', icon_color='white', icon=activity_icon, prefix='fa')).add_to(mymap)

        folium.LayerControl(collapsed=False).add_to(mymap)
        mymap.save( map_path ) # saves to html file for display below

# %% [markdown]
# ## Main

# %%
import os
import requests
import json
import gpxpy
import folium
from folium import plugins
from math import sin, cos, sqrt, atan2, radians
import argparse
import webbrowser

def main():
    
    parser = argparse.ArgumentParser(
        description='Find closest tracks/routes that pass withing a specified distance of a location',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--path', '-p', type=str, default='tracks', help="directory containing GPX tracks/routes")
    parser.add_argument('--location', '-l', nargs=2, type=float, default=[0, 0], help="latitude and longitude of target")
    parser.add_argument('--dist', '-d', type=int, default='800', help='min distance in meters track needs to be tospecified point to match')
    parser.add_argument('--output', '-o', type=str, default='routes.html', help="name of HTML file to generate (including path relative to current directory)")
    parser.add_argument('--refresh', '-r', action='store_true', help='refresh routes from RWGPS')
    parser.add_argument('--max', '-m', type=int, default=10, help='find the best # routes')
    
    args = parser.parse_args()
    #args = parser.parse_args(['-r'])
    
    #refresh our list of tracks from RWGPS
    #refresh_rwgps_routes( args.path, api_key = 'testkey1', auth_token='1869bd7dd7795934a4b2cb311cd5cd7f' )
    if args.refresh:
        refresh_rwgps_routes( args.path )

    # OK - now we loop through our tracks and look for one that's near our destination...
    if (args.location[0] != 0):
        matches = find_close_routes ( args.path, args.location[0], args.location[1], args.dist, args.max )
    else:
        matches = None
         
    #matches = ['36216168.gpx', '32408351.gpx', '43141887.gpx', 'Back_to_Brinkley.gpx', '11764387.gpx', '11775438.gpx', '35648012.gpx', '35592301.gpx']
    #matches = ['Back_to_Brinkley.gpx']

    # Now make a map with the selected routes on it...
    if matches :
        print (f"Matched tracks: {matches}")
        map = make_folium_map ( args.path, matches, args.output, match_point = (args.location[0], args.location[1]), marker_text = f'Closest {args.max} routes within {args.dist:.0f}m of here (lat:{args.location[0]:.4f}, lon:{args.location[1]:.4f}' )
        print (f"Map {args.output} created")
        webbrowser.open(args.output)
    else :
        print ("No matches")

if (__name__ == '__main__'):
   main()



