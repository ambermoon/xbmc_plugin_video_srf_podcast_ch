#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import json
import urllib
import urllib2
import socket
import re
import xml.etree.ElementTree as ET
import xbmc
import xbmcplugin
import xbmcgui
import xbmcaddon
import os
import traceback
from StringIO import StringIO 
import gzip
from urlparse import urlparse 

#'Base settings'
#'Start of the plugin functionality is at the end of the file'
addon = xbmcaddon.Addon()
addonID = 'plugin.video.srf_podcast_ch'
pluginhandle = int(sys.argv[1])
socket.setdefaulttimeout(30)
translation = addon.getLocalizedString
xbmcplugin.setPluginCategory(pluginhandle,"News")
xbmcplugin.setContent(pluginhandle,"tvshows")
addon_work_folder = xbmc.translatePath("special://profile/addon_data/"+addonID)
if not os.path.isdir(addon_work_folder):
    os.mkdir(addon_work_folder)
FavoritesFile = xbmc.translatePath("special://profile/addon_data/"+addonID+"/"+addonID+".favorites")
showSubtitles = addon.getSetting("showSubtitles") == "true"
forceViewMode = addon.getSetting("forceView") == "true"
viewModeShows = str(addon.getSetting("viewIDShows"))
numberOfEpisodesPerPage = str(addon.getSetting("numberOfShowsPerPage"))

#'this method list all SRF-channel when SRF-Podcast was selected in the main menu'
def chooseChannel():
    addChannel('srf', 'SRF', 'chooseOptions')
    addChannel('rts', 'RTS', 'chooseOptions')
    addChannel('rsi', 'RSI', 'chooseOptions')
    addChannel('rtr', 'RTR', 'chooseOptions')
    xbmcplugin.endOfDirectory(handle=pluginhandle, succeeded=True)

def chooseOptions(channel):
	addOption('dummy',addon.getLocalizedString(30008), 'listTvShows',channel,1)
	addOption('dummy',addon.getLocalizedString(30005), 'newestTvShows',channel,1)
	addOption('dummy',addon.getLocalizedString(30007), 'mostClickedTvShows',channel,1)
	addOption('dummy',addon.getLocalizedString(30006), 'recommendedTvShows',channel,1)
	addOption('c49c1d73-2f70-0001-138a-15e0c4ccd3d0','Live', 'liveTvShows',channel,1)
	xbmcplugin.endOfDirectory(handle=pluginhandle, succeeded=True)
	
#'this method list all TV shows available for selected channel'
def listTvShows(channel):
	url = 'http://il.srgssr.ch/integrationlayer/1.0/ue/' + channel + '/tv/assetGroup/editorialPlayerAlphabetical.json'
	response = json.load(open_srf_url(url))
	shows =  response["AssetGroups"]["Show"]
	title = ''
	desc = ''
	picture = ''
	page = 1
	mode = 'listEpisodes'
	for show in shows:
		try:
			title = show['title']
		except:
			title = 'No Title'
		try:
			desc = show['description']
		except:
			desc = 'No Description'
		try:
			picture = clean_picture_url(show['Image']['ImageRepresentations']['ImageRepresentation'][0]['url'])
		except:
			picture = ''
		addShow(title, show['id'], mode, desc, picture,page,channel)
		
	xbmcplugin.addSortMethod(pluginhandle,1)
	xbmcplugin.endOfDirectory(pluginhandle)
	if forceViewMode:
		xbmc.executebuiltin('Container.SetViewMode('+viewModeShows+')')

#'this method list all TV shows available for selected channel and mode'
def listVideosByMode(channel,mode,page):
	url = ''
	if mode == 'recommendedTvShows':
		url = 'http://il.srgssr.ch/integrationlayer/1.0/ue/' + channel + '/video/editorialPlayerPicks.json'
	elif mode == 'newestTvShows':
		url = 'http://il.srgssr.ch/integrationlayer/1.0/ue/' + channel + '/video/editorialPlayerLatest.json?pageNumber='+str(page)+'&pageSize='+str(numberOfEpisodesPerPage)
	elif mode == 'mostClickedTvShows':
		url = 'http://il.srgssr.ch/integrationlayer/1.0/ue/' + channel + '/video/mostClicked.json?pageSize='+str(numberOfEpisodesPerPage)
	
	response = json.load(open_srf_url(url))
	videos =  response["Videos"]["Video"]
	title = ''
	desc = ''
	picture = ''
	mode = 'playepisode'
	for video in videos:
		try:
			title = video['AssetMetadatas']['AssetMetadata'][0]['title']
		except:
			title = 'No Title'
		try:
			desc = video['AssetMetadatas']['AssetMetadata'][0]['description']
		except:
			desc = 'No Description'
		try:
			picture = clean_picture_url(video['Image']['ImageRepresentations']['ImageRepresentation'][0]['url'])
		except:
			picture = ''
		try:
			length = int(video['duration']) / 1000 / 60
		except:
			length = 0
		try:
			pubdate = video['AssetSet']['publishedDate']
		except:
			pubdate = ''		
		addLink(title, video['id'], 'playepisode', desc, picture, length, pubdate,showbackground,channel)
			
	xbmcplugin.addSortMethod(pluginhandle,1)
	xbmcplugin.endOfDirectory(pluginhandle)
	if forceViewMode:
		xbmc.executebuiltin('Container.SetViewMode('+viewModeShows+')')

#'this method list all live streams available for selected channel'
def listLiveStreams(channel):
	url = 'http://il.srgssr.ch/integrationlayer/1.0/ue/' + channel + '/video/livestream.json'
	
	response = json.load(open_srf_url(url))
	videos =  response["Videos"]["Video"]
	title = ''
	desc = ''
	picture = ''
	pubdate = ''
	length = 0
	mode = 'playepisode'
	for video in videos:
		try:
			title = video['AssetSet']['Rubric']['title']
		except:
			title = 'No Title'
		try:
			picture = clean_picture_url(video['AssetSet']['Rubric']['PrimaryChannel']['Image']['ImageRepresentations']['ImageRepresentation'][0]['url'])
		except:
			picture = ''	
		addLink(title, video['id'], 'playepisode', desc, picture, length, pubdate,showbackground,channel)
			
	xbmcplugin.addSortMethod(pluginhandle,1)
	xbmcplugin.endOfDirectory(pluginhandle)
	if forceViewMode:
		xbmc.executebuiltin('Container.SetViewMode('+viewModeShows+')')
		
#'this method list all episodes of the selected show'
def listEpisodes(channel,showid,showbackground,page):
	url = 'http://il.srgssr.ch/integrationlayer/1.0/ue/' + channel + '/assetSet/listByAssetGroup/'+showid+'.json?pageNumber='+str(page)+"&pageSize="+str(numberOfEpisodesPerPage)
	response = json.load(open_srf_url(url))
	maxpage = 1
	try:
		maxpage = response["AssetSets"]["@maxPageNumber"]
	except:
		maxpage = 0

	show =  response["AssetSets"]["AssetSet"]
		
	for episode in show:
		title = episode['title']
		url = ''
		desc = ''
		picture = '' 
		pubdate = episode['publishedDate']
		
		try:
			desc = episode['Assets']['Video'][0]['AssetMetadatas']['AssetMetadata'][0]['description']
		except:
			desc = 'No Description'
		try:
			picture = clean_picture_url(episode['Assets']['Video'][0]['Image']['ImageRepresentations']['ImageRepresentation'][0]['url'])
		except:
			# no picture
			picture = ''
		try:
			length = int(episode['Assets']['Video'][0]['duration']) / 1000 / 60
		except:
			length = 0
		try:
			url = episode['Assets']['Video'][0]['id']
		except:
			url = 'no url'
		try:
			titleextended = ' - ' + episode['Assets']['Video'][0]['AssetMetadatas']['AssetMetadata'][0]['title']
		except:
			titleextended = ''
	
		addLink(title+titleextended, url, 'playepisode', desc, picture, length, pubdate,showbackground,channel)

	# check if another page is available
	page = int(page)
	maxpage = int(maxpage)
	if page < maxpage or maxpage == 0 and len(show) == int(numberOfEpisodesPerPage):
		page = page + 1
		addnextpage(addon.getLocalizedString(33001).format(page,maxpage), showid, 'listEpisodes', '', showbackground,page,channel)
	
	xbmcplugin.endOfDirectory(pluginhandle)
	if forceViewMode:
		xbmc.executebuiltin('Container.SetViewMode('+viewModeShows+')')
	
#'this method plays the selected episode'
def playepisode(channel,episodeid):
	besturl = ''
	
	try:
		url = 'http://il.srgssr.ch/integrationlayer/1.0/ue/' + channel + '/video/play/' + episodeid + '.json'
		response = json.load(open_srf_url(url))
		playlistVector = response['Video']['Playlists']['Playlist']
		
		# filter objects with list comprehensions
		playlist = [obj for obj in playlistVector if obj['@protocol'] == 'HTTP-HLS']
		
		playlistVector = playlist[0]
		urls = playlistVector['url']
		
		besturl = urls[0]['text']
		for tempurl in urls:
			if tempurl['@quality'] == 'HD':
				besturl = tempurl['text']
				break
		
	except:
		print "not for download"

	if besturl == '':
		try:
			url = 'http://il.srgssr.ch/integrationlayer/1.0/ue/' + channel + '/video/play/' + episodeid + '.json'
			response = json.load(open_srf_url(url))
			urls =  response['Video']['Playlists']['Playlist'][0]['url']
			
			besturl = urls[0]['text']
			for tempurl in urls:
				if tempurl['@quality'] == 'HD':
					besturl = tempurl['text']
					break
			
		except:
			print "not for download"

	# add authentication token for akamaihd
	if "akamaihd" in urlparse(besturl).netloc:
		url = "http://tp.srgssr.ch/akahd/token?acl=" + urlparse(besturl).path 
		response = json.load(open_srf_url(url))
		token = response["token"]["authparams"]
		besturl = besturl + '?' + token 
	
	listitem = xbmcgui.ListItem(path=besturl)
	xbmcplugin.setResolvedUrl(pluginhandle, True, listitem)

#'helper method to create a network-item in the list
def addChannel(id, name, mode):
    ok = True
    directoryurl = sys.argv[0]+"?channel="+urllib.quote_plus(id)+"&mode="+str(mode)
    liz = xbmcgui.ListItem(name)
    ok = xbmcplugin.addDirectoryItem(pluginhandle, url=directoryurl, listitem=liz, isFolder=True)
    return ok
	
def addOption(url, name, mode,channel,page):
    ok = True
    directoryurl = sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&channel="+str(channel)+"&page="+str(page)
    liz = xbmcgui.ListItem(name)
    ok = xbmcplugin.addDirectoryItem(pluginhandle, url=directoryurl, listitem=liz, isFolder=True)
    return ok
	
#'helper method to create a folder with subitems'
def addShow(name, url, mode, desc, iconimage,page,channel):
    ok = True
    directoryurl = sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&showbackground="+urllib.quote_plus(iconimage)+"&page="+str(page)+"&channel="+str(channel)
    liz = xbmcgui.ListItem(name)
    liz.setIconImage("DefaultFolder.png")
    liz.setThumbnailImage(iconimage)
    liz.setLabel2(desc)
    liz.setArt({'poster' : iconimage , 'banner' : iconimage, 'fanart' : iconimage, 'thumb' : iconimage})
    liz.setInfo(type="Video", infoLabels={"title": name, "plot": desc, "plotoutline": desc})
    xbmcplugin.setContent(pluginhandle, 'tvshows')
    ok = xbmcplugin.addDirectoryItem(pluginhandle, url=directoryurl, listitem=liz, isFolder=True)
    return ok

#'helper method to create a folder with subitems'
def addnextpage(name, url, mode, desc, showbackground,page,channel):
	ok = True
	directoryurl = sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&showbackground="+urllib.quote_plus(showbackground)+"&page="+str(page)+"&channel="+str(channel)
	liz = xbmcgui.ListItem(name)
	liz.setLabel2(desc)
	#liz.setArt({'poster' : '' , 'banner' : '', 'fanart' : showbackground, 'thumb' : ''})
	liz.setInfo(type="Video", infoLabels={"title": name, "plot": desc, "plotoutline": desc})
	xbmcplugin.setContent(pluginhandle, 'episodes')
	ok = xbmcplugin.addDirectoryItem(pluginhandle, url=directoryurl, listitem=liz, isFolder=True)
	return ok
    
#'helper method to create an item in the list'
def addLink(name, url, mode, desc, iconurl, length, pubdate, showbackground,channel):
	ok = True
	linkurl = sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&channel="+str(channel)
	liz = xbmcgui.ListItem(name)
	liz.setIconImage('')
	liz.setThumbnailImage(iconurl)
	liz.setLabel2(desc)
	liz.setArt({'poster' : iconurl , 'banner' : iconurl, 'fanart' : showbackground, 'thumb' : iconurl})
	liz.setInfo(type='Video', infoLabels={"Title": name, "Duration": length, "Plot": desc, "Aired" : pubdate})
	liz.setProperty('IsPlayable', 'true')
	xbmcplugin.setContent(pluginhandle,'episodes')
	ok = xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=linkurl, listitem=liz)
	return ok

#'helper method to retrieve parameters in a dict from the arguments given to this plugin by xbmc'
def parameters_string_to_dict(parameters):
    paramDict = {}
    if parameters:
        paramPairs = parameters[1:].split("&")
        for paramsPair in paramPairs:
            paramSplits = paramsPair.split('=')
            if (len(paramSplits)) == 2:
                paramDict[paramSplits[0]] = paramSplits[1]
    return paramDict

def open_srf_url(urlstring):
    request = urllib2.Request(urlstring) 
    request.add_header('Accept-encoding', 'gzip') 
    response = ''
    try:
        response = urllib2.urlopen(urlstring) 
        if response.info().get('Content-Encoding') == 'gzip': 
            buf = StringIO( response.read()) 
            f = gzip.GzipFile(fileobj=buf) 
            response = StringIO(f.read())
    except Exception as e:
        print traceback.format_exc()
        dialog = xbmcgui.Dialog().ok('xStream Error',str(e.__class__.__name__),str(e))
	
    return response

def clean_picture_url(urlstring):
    return re.sub('/16x9$','',urlstring)

#'Start'
#'What to do... if nothing is given we start with the index'
params = parameters_string_to_dict(sys.argv[2])
mode = params.get('mode', '')
url = params.get('url', '')
channel = params.get('channel', '')
showbackground = urllib.unquote_plus(params.get('showbackground', ''))
page = params.get('page', '')

#mode = urllib.unquote_plus(params.get('mode', ''))
#url = urllib.unquote_plus(params.get('url', ''))
#name = urllib.unquote_plus(params.get('name', ''))

if mode == 'chooseChannel':
    chooseChannel()
elif mode == 'chooseOptions':
    chooseOptions(channel)
elif mode == 'recommendedTvShows':
    listVideosByMode(channel,mode,page)
elif mode == 'newestTvShows':
    listVideosByMode(channel,mode,page)
elif mode == 'mostClickedTvShows':
    listVideosByMode(channel,mode,page)
elif mode == 'liveTvShows':
    listLiveStreams(channel)
elif mode == 'listTvShows':
    listTvShows(channel)
elif mode == 'listEpisodes':
    listEpisodes(channel,url,showbackground,page)
elif mode == 'playepisode':
    playepisode(channel,url)
else:
    chooseChannel()
