

import json

import requests
from bs4 import BeautifulSoup as soup
from geopy import geocoders
import os

class LocatorSetup:
    """The (poorly named) class containing the methods used to format and save the data from the first
    time setup into a user_settings file"""
    def __init__(self):
        self.state_pairs = {}
        self.abbreviation_to_state = {}
        self.state_to_abbreviation = {}
        self.user_location = [None, None]
        self.bands = []
        self.concert_notification_time_to_display = 2
        self.last_checked = None
        self.removed_bands = []
        self.spotify_id = None
        try:
            with open(os.path.join('userdata','user_settings'),'r') as settings:
                data = json.load(settings)
                for key,value in data.items():
                    if key == 'last_checked':
                        self.last_checked = value
                    else:
                        exec(f'self.{key} = {value}')

        except FileNotFoundError:
            pass


    def __call__(self):
        """If the user_settings file already exists this does nothing, but otherwise gets the required
        user info and saves to to a JSON file. Note this should only ever be called by the GUI, individual methods
        should be called directly, if needed."""

        self.state_pairs_find()
        self.state_abbreviation_associations()
        location = yield
        self.user_location_set(location)
        self.spotify_id = yield
        bands = yield
        self.get_bands(bands)
        yield
        self.save_data()



    def state_pairs_find(self):
        """Generates a list of adjacent states for use with narrowing down the locations to be searched in order
        to limit queries to geolocators"""
        states = requests.get('https://state.1keydata.com/bordering-states-list.php', verify=False)
        stsoup = soup(states.text,features="html.parser")
        stsoup = stsoup.select("table[class='content4']")
        stsoup = stsoup[0].select("tr")
        for subsoup in stsoup[1:]:
            sres = subsoup.select('td')
            self.state_pairs[sres[0].string] = tuple(sres[1].string.split(', '))

    def state_abbreviation_associations(self):
        """Generates a dictionary of state full names to abbreviations"""
        sabv = requests.get('https://abbreviations.yourdictionary.com/articles/state-abbrev.html')
        assocs = soup(sabv.text,features="html.parser")
        assocs = assocs.select('ul')
        for pairs in assocs[0].select('li'):
            pairs = pairs.string.split(' - ')
            self.state_to_abbreviation[pairs[0]] = pairs[1][:-1]
            self.abbreviation_to_state[pairs[1][:-1]] = pairs[0]

    def user_location_set(self,location):
        # TODO - find out what this returns for non-existant places (i.e. typos in user input)
        """Finds user location (latitude,longitude) via Nominatim"""
        if location:
            userloc = geocoders.Nominatim(user_agent="testing_location_find_10230950239").geocode(location,True)
            self.user_location[0] = tuple(abv for abv in self.abbreviation_to_state.keys()
                                     if abv in location or self.abbreviation_to_state[abv] in location)
            if not self.user_location[0]: self.user_location[0] = 'none'
            self.user_location[1] = (userloc.latitude,userloc.longitude)
        else:
            self.user_location = ['Not Specified',('Not Specified','Not Specified')]

    def get_bands(self,bands=None):
        """ Creating a list of bands for which concert info is wanted"""
        [self.bands.append(band) for band in bands if band not in self.bands and band not in self.removed_bands]

    def save_data(self):
        "Saves user data to a JSON file"
        data = {'state_pairs':self.state_pairs,
                 'user_location':self.user_location,
                 'state_to_abbreviation':self.state_to_abbreviation,
                 'abbreviation_to_state':self.abbreviation_to_state,
                 'bands':list(set(self.bands)),
                'spotify_id':self.spotify_id,
                'last_checked':self.last_checked,
                'concert_notification_time_to_display':self.concert_notification_time_to_display,# weeks, default time until concert to present notifications
                'removed_bands':self.removed_bands}
        with open(os.path.join('userdata','user_settings'),'w') as settings:
            json.dump(data,settings)

class LocatorMain(LocatorSetup):
    ''' This class is essentially a container for all the operations required by the GUI, with
    some stuff recycled from the class that is used for first time setup (LocatorSetup). Notable differences include
    that the class itself is not callable, as all methods are called directly by the corresponding GUI element'''


    def __call__(self):
        pass # Not Callable

    def update_user_location(self,location):
        '''Changes user location'''
        # TODO - currently setting it like this wont update location for already tracked concerts, either
        # TODO find a way to track multiple or dump all the tables & start fresh
        super().user_location_set(location)
        self.save_data()

    def remove_spotify_tracking(self):
        self.spotify_user_id = None
        self.save_data()

    def save_spotify_username(self,user_id):
        self.spotify_user_id = user_id
        self.save_data()

    def add_bands(self,bands):
        super().get_bands(bands)
        self.save_data()

    def remove_bands(self,bands):
        [self.removed_bands.append(band) for band in bands]
        self.bands = [band for band in self.bands if band not in self.removed_bands]
        self.save_data()

    def add_removed_bands(self,bands):
        [self.removed_bands.remove(band) for band in bands]
        super().get_bands(bands)
        self.save_data()

    def change_time_to_display(self,ttd):
        'changes the range of dates for which notifications will be given'
        self.concert_notification_time_to_display = ttd
        self.save_data()

if __name__ == '__main__':
    l = LocatorMain()
    l.save_data()