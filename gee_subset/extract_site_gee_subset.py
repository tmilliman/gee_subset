#!/usr/bin/env python

"""
Script to extract Band1,2,3 reflectances from the MODIS collection 6 MCD43A4
image collection on Google Earth Engine (GEE).  The output files are
used by phenocam_explorer to compare MODIS EVI/NDVI to the gcc indices
we calculate.

In collection 5 there were only values every 8 days.  For collection 6
we get daily values hence many more layers to deal with. The idea is
to split the collection by year in a loop, grab the values and
concat to a single dataframe.
"""

# load required libraries
import os
import sys
import argparse
from datetime import date
import requests
import pandas as pd
import ee

# mostly use Koen's gee_subset package script functions
from gee_subset import gee_subset


def get_siteinfo(sitename):
    """
    Use PhenoCam API to get the site info.  In particular
    we would like to get the lat, lon, start_date, and 
    end_date for this is site.
    """

    infourl = ("https://phenocam.sr.unh.edu/api/cameras/" +
               "?Sitename__iexact={}".format(sitename))
    response = requests.get(infourl)
    if response.status_code != 200:
        errmsg = "Error getting site info for {}.\n".format(sitename)
        sys.stderr.write(errmsg)
        errmsg = "HTTP Status_code: {}\n".format(response.status_code)
        sys.stderr.write(errmsg)
        return None

    info_json = response.json()
    if info_json['count'] == 0:
        errmsg = "Site {} not found.\n".format(sitename)
        sys.stderr.write(errmsg)
        sys.exit
        
    return info_json

if __name__ == "__main__":

    # set up command arguments
    parser = argparse.ArgumentParser(
        description="""Extract reflectances to be used to
        create EVI and NDVI time series for a sites location.""",
        epilog="""Using the github repo of Koen Hufkens
        (https://github.com/khufkens/gee_subset)"""
    )

    parser.add_argument('-v',
                        '--verbose',
                        help='''verbose debugging''',
                        default=False,
                        action="store_true")

    parser.add_argument('sitename',
                        help="PhenoCam site name")

    args = parser.parse_args()
    verbose = args.verbose
    sitename = args.sitename
    
    if verbose:
        print("Verbose: {}".format(verbose))
        print("Site Name: {}".format(sitename))

    # get info for this site
    site_info = get_siteinfo(sitename)
    if site_info is None:
        sys.exit()
    else:
        results = site_info['results'][0]
        lat = results['Lat']
        lon = results['Lon']
        date_first = results['date_first']
        date_last = results['date_last']

    if verbose:
        print("Lat: {}".format(lat))
        print("Lon: {}".format(lon))
        print("Date First: {}".format(date_first))
        print("Date Last: {}".format(date_last))

    start_year = int(date_first.split('-')[0])
    end_year = 2017
    bands = tuple(['Nadir_Reflectance_Band1',
                   'Nadir_Reflectance_Band2',
                   'Nadir_Reflectance_Band3'])
    product = "MODIS/006/MCD43A4"

    # initialize GEE session
    # this should open a browser window if there is no
    # valid refresh token stored in ~/.config/earthengine/credentials
    ee.Initialize()

    df = None
    for year in range(start_year, end_year + 1):
        print("year: {}".format(year))
        ydf = gee_subset(product=product,
                         bands=bands,
                         start_date="{}-01-01".format(year),
                         end_date="{}-01-01".format(year+1),
                         latitude=float(lat),
                         longitude=float(lon),
                         scale=500,
                         pad=0)

        if df is None:
            df = ydf
        else:
            df = pd.concat([df, ydf])

    outfile = "./modis_time_series/{}_gee_subset.csv".format(sitename)
    df.to_csv(outfile, index=False)

    nlines = len(df)
    print("{} lines saved to output file".format(nlines))
