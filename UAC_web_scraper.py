# -*- coding: utf-8 -*-
"""
Created on Thu Jun 14 12:02:50 2018
Author: Ross Palomaki

UAC Web Scraper

This script scrapes avalanche report data from the Utah Avalanche Center 
website and saves data from all reports in a pandas DataFrame object.
"""

from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from urllib.request import urlopen, Request
from urllib.error import HTTPError
import re
import time
from datetime import datetime
import unicodedata as ucd


#Setup headers for url request headers when accessing webpages
#https://stackoverflow.com/a/32026467
request_headers = {
"Accept-Language": "en-US,en;q=0.5",
"User-Agent": "Avalanche Data extractor (ross.palomaki@gmail.com)",
"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
"Referer": "http://utahavalanchecenter.org",
"Connection": "keep-alive" 
}


#Open list of all avalanches on UAC website
avy_list_webpage = Request('https://utahavalanchecenter.org/avalanches/list', headers=request_headers)
soup2 = BeautifulSoup(urlopen(avy_list_webpage), 'html.parser')
time.sleep(2)
#Find all links - individual avy reports are accessed by links off main page
links = soup2.find_all('a')
#Gather only avalanche reports from full list of links
avy_reports = [re.findall('\/avalanches\/[0-9]{5}', str(tag))[0] for tag in links if re.findall('avalanches\/[0-9]{5}', str(tag))]


#Prepare to loop through all reports
http_errors = [] #List to hold reports that result in HTTP error when connecting
mismatched = [] #List to hold reports with mismatched number of items/labels
avy_data = 0 #Later, will be a pd.DataFrame object to hold report data
i = 0 #page counter

#Cycle through all reports to gather data
count = 0
for report in avy_reports:
    #Open webpage
    try:
        report_webpage = Request('https://utahavalanchecenter.org/'+report, headers=request_headers)
        soup = BeautifulSoup(urlopen(report_webpage), 'html.parser')
    except HTTPError:
        http_errors.append(report)
        continue
    
    #Gather report information
    field_labels = soup.find_all('div', attrs={'class':'field-label'}) #Report headings
    field_items = soup.find_all('div', attrs={'class':'field-item even'}) #Information
    #Create lists of text elements from field labels and items
    labels = [re.findall('\D+:',lab.text)[0][:-1] for lab in field_labels] #Index on [:-1] to remove trailing ':'
    #Remove 'Coordinates' label from list - add true coordinates in later
    del labels[labels.index('Coordinates')]
    #Use boolean expression to only collect non-empty item strings, and those that are not JS code (e.g. photos)
    #ucd.normalize: https://stackoverflow.com/a/34669482   https://docs.python.org/2/library/unicodedata.html#unicodedata.normalize
    items = [ucd.normalize('NFKD', item.text) for item in field_items if (item.text and 'OpenLayers' not in item.text)]
    
    #Extract lat/lon coords using script headings
    coords_present = 0
    scripts = soup.find_all('script', attrs={'type':'text/javascript'})
    for tag in scripts:
        if 'wkt' in str(tag):
            coords_present = 1
            coords = re.findall('\(\S+\s[0-9]+\S[0-9]+', str(tag))[0][1:] #Index on [1:] to remove leading '('
            lon, lat = coords.split(' ')
    #Add lat and lon to labels and items lists, if coords given in report
    if coords_present:
        labels.extend(['Lat','Lon'])
        items.extend([str(lat), str(lon)])

    #Check to see if number of labels and items match. If not, skip this report for now.
    if len(labels) != len(items):
        mismatched.append(report)
        continue
            
    #Add in report number to labels and items
    labels.append('UAC Report Number')
    items.append(re.findall('[0-9]+', report)[0])
    
    #Store items in avy_data, with labels as the columns
    if type(avy_data) == int:
        avy_data = pd.DataFrame(items, index=labels).T
    else:
        #Create df with report data
        report_data = pd.DataFrame(items, index=labels).T
        #Check for and drop duplicated columns
        report_data = report_data.loc[:,~report_data.columns.duplicated()]
        #Concat current report to other reports
        avy_data = pd.concat([avy_data, report_data], join='outer')
        avy_data.index = np.arange(len(avy_data))
    
    #Print progress:
    if not count%10:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '===== page: %i' %i, '===== report number: %i' %count)
    
    #To be courteous, wait a couple seconds before accessing the UAC server again
    time.sleep(2)
    count += 1



#Front page of the avalanche list is collected. But, 38 pages to go!
num_pages = 38
for i in range(1, num_pages):

    avy_list_webpage = Request('https://utahavalanchecenter.org/avalanches/list?page=%i' %i, headers=request_headers)
    soup2 = BeautifulSoup(urlopen(avy_list_webpage), 'html.parser')
    time.sleep(2)
    #Find all links - individual avy reports are accessed by links off main page
    links = soup2.find_all('a')
    #Gather only avalanche reports from full list of links
    avy_reports = [re.findall('\/avalanches\/[0-9]{5}', str(tag))[0] for tag in links if re.findall('avalanches\/[0-9]{5}', str(tag))]
    
    count = 0
    for report in avy_reports:
    #Open webpage
        try:
            report_webpage = Request('https://utahavalanchecenter.org/'+report, headers=request_headers)
            soup = BeautifulSoup(urlopen(report_webpage), 'html.parser')
        except HTTPError:
            http_errors.append(report)
            continue
        
        #Gather report information
        field_labels = soup.find_all('div', attrs={'class':'field-label'}) #Report headings
        field_items = soup.find_all('div', attrs={'class':'field-item even'}) #Information
        #Create lists of text elements from field labels and items
        labels = [re.findall('\D+:',lab.text)[0][:-1] for lab in field_labels] #Index on [:-1] to remove trailing ':'
        #Remove 'Coordinates' label from list - add true coordinates in later
        del labels[labels.index('Coordinates')]
        #Use boolean expression to only collect non-empty item strings, and those that are not JS code (e.g. photos)
        #ucd.normalize: https://stackoverflow.com/a/34669482   https://docs.python.org/2/library/unicodedata.html#unicodedata.normalize
        items = [ucd.normalize('NFKD', item.text) for item in field_items if (item.text and 'OpenLayers' not in item.text)]
        
        #Extract lat/lon coords using script headings
        coords_present = 0
        scripts = soup.find_all('script', attrs={'type':'text/javascript'})
        for tag in scripts:
            if 'wkt' in str(tag):
                coords_present = 1
                try:
                    coords = re.findall('\(\S+\s[0-9]+\S[0-9]+', str(tag))[0][1:] #Index on [1:] to remove leading '('
                except IndexError:
                    coords = re.findall('\(\S+\s\S+\)', str(tag))[0][1:-1]
                lon, lat = coords.split(' ')
        #Add lat and lon to labels and items lists, if coords given in report
        if coords_present:
            labels.extend(['Lat','Lon'])
            items.extend([str(lat), str(lon)])
        
        #Add in report number to labels and items
        labels.append('UAC Report Number')
        items.append(re.findall('[0-9]+', report)[0])
    
        #Check to see if number of labels and items match. If not, skip this report for now.
        if len(labels) != len(items):
            mismatched.append(report)
            continue
        
        #Store items in avy_data, with labels as the columns
        #Create df with report data
        report_data = pd.DataFrame(items, index=labels).T
        #Check for and drop duplicated columns
        report_data = report_data.loc[:,~report_data.columns.duplicated()]
        #Concat current report to other reports
        avy_data = pd.concat([avy_data, report_data], join='outer')
        avy_data.index = np.arange(len(avy_data))
        
        #Print progress:
        if not count%10:
            print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '===== page: %i' %i, '===== report number: %i' %count)
            
        #To be courteous, wait a couple seconds before accessing the UAC server again
        time.sleep(2)
        count += 1


#Save completed avalanche data and list of mismatched reports
avy_data.to_csv('avy_data.csv')
pd.Series(mismatched).to_csv('mismatched.csv')













