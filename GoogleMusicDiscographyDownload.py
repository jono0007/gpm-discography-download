# Initialize api and login with oauth_login
from gmusicapi import Mobileclient, CallFailure, exceptions
from urllib.request import urlretrieve, urlopen
from urllib.error import HTTPError,URLError
from mutagen import id3,mp3,File
import os

api = Mobileclient()
if not os.path.exists(api.OAUTH_FILEPATH):
    api.perform_oauth()
if not os.path.exists(api.OAUTH_FILEPATH[:-17] + 'deviceID.txt'):
    try:
        api.oauth_login('')
    except exceptions.InvalidDeviceId as error:
        deviceID = error.valid_device_ids[0]
        output = open(api.OAUTH_FILEPATH[:-17] + 'deviceID.txt', 'w')
        output.write(deviceID)
        output.close()
else:
    deviceID = open(api.OAUTH_FILEPATH[:-17] + 'deviceID.txt').readlines()
api.oauth_login(deviceID)

def clean(string):
    # Replace chars with alternatives - "<>:\"/|?*"
    string = string.replace('<', '‹')
    string = string.replace('>', '›')
    string = string.replace(':', '꞉')
    string = string.replace('"', '\'')
    string = string.replace('/', '∕')
    string = string.replace('\\', '⧹')
    string = string.replace('|', 'ǀ')
    string = string.replace('?', '⁇')
    string = string.replace('*', '∗')
    string = string.replace('...', '…')
    string = string.rstrip()
    string = string[:100]
    return string

artist = input('Enter artist ID or artist name to search: ')

# Check for artist ID, search for one if needed
if not len(artist) == 27 and not artist[0] == 'A':
    # Attempt to search artist name and pull first result
    try:
        artistID = api.search(artist)['artist_hits'][0]['artist']['artistId']
    except:
        print("No search results for " + artist + '\nTry getting Artist ID from artist\'s Google Music page URL.\nIt starts with A and is 27 characters.')
        exit()
else:
    artistID = artist

# Use artist ID to retrieve all album IDs
albumIDs = []
try:
    for album in api.get_artist_info(artistID,True,0,0)['albums']:
        albumIDs.append(album['albumId'])
except KeyError:
    print("No albums for " + artist)
    exit()
except:
    print("Critical error for " + artist)
    print(error)
    exit()

# Use album IDs to get track IDs
trackIDs = []
for albumID in albumIDs:
    try:
        for track in api.get_album_info(albumID)['tracks']:
            trackIDs.append(track['storeId'])
    except KeyError:
        print(albumID + ' has no tracks')
    except HTTPError as error:
        print(error)
    except CallFailure as error:
        print(error)

# Download using get_url_stream
downDir = input('Enter download directory: ')
if not downDir.endswith('\\'): downDir += '\\'
totalTracks = len(trackIDs)
for i in range(totalTracks):
    try:
        trackInfo = api.get_track_info(trackIDs[0])
    except:
        print("Error occurred getting info for " + trackIDs[0] + ". Skipping...")
        del trackIDs[0]
        continue
    id3Title = str(trackInfo['title'])
    id3Artist = str(trackInfo['artist'])
    id3Composer = str(trackInfo['composer'])
    id3Album = str(trackInfo['album'])
    id3AlbumArtist = str(trackInfo['albumArtist'])
    try:
        id3Year = str(trackInfo['year'])
    except KeyError:
        id3Year = ''
        print("No year tag")
    id3TrackNumber = str(trackInfo['trackNumber'])
    id3DiscNumber = str(trackInfo['discNumber'])
    try:
        id3AlbumCover = urlopen(trackInfo['albumArtRef'][0]['url']).read()
    except:
        id3AlbumCover = False
        print("No Album Cover!")
    try:
        id3Genre = str(trackInfo['genre'])
    except KeyError:
        id3Genre = False
        print("No genre tag")
    dirPath = downDir + clean(id3Artist) + "\\[" + id3Year + "] " + clean(id3Album) + "\\"
    if not os.path.exists(dirPath):
        os.makedirs(dirPath)
    fileName = str(id3TrackNumber) + ". " + clean(id3Title) + ".mp3"
    filePath = dirPath + fileName
    if os.path.exists(filePath):
        print("Song already exists! Skipping...")
        del trackIDs[0]
        continue
    print("Downloading song " + str(i+1) + " of " + str(totalTracks) + ": " + id3Title + " by " + id3Artist)
    try:
        url = api.get_stream_url(trackIDs[0])
        urlretrieve(url, filePath)
    except:
        print("Error occurred downloading trackID " + trackIDs[0] + ". Skipping...")
        del trackIDs[0]
        continue
    errorTrack = 0
    mp3File = File(filePath)
    mp3File.add_tags()
    mp3File.tags.add(id3.TIT2(encoding=3,text=id3Title))
    mp3File.tags.add(id3.TALB(encoding=3,text=id3Album))
    mp3File.tags.add(id3.TPE1(encoding=3,text=id3Artist))
    mp3File.tags.add(id3.TPE2(encoding=3,text=id3AlbumArtist))
    mp3File.tags.add(id3.TCOM(encoding=3,text=id3Composer))
    if id3Genre:
        mp3File.tags.add(id3.TCON(encoding=3,text=id3Genre))
    if id3Year:
        mp3File.tags.add(id3.TYER(encoding=3,text=id3Year))
    mp3File.tags.add(id3.TRCK(encoding=3,text=id3TrackNumber))
    mp3File.tags.add(id3.TPOS(encoding=3,text=id3DiscNumber))
    if id3AlbumCover:
        mp3File.tags.add(id3.APIC(mime='image/jpeg',type=3,desc=u'Cover',data=id3AlbumCover))
    mp3File.save()
    del trackIDs[0]
