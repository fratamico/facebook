#import csv
import unicodecsv as csv
import datetime
import json
import time
import urllib2

from os import listdir
from os.path import isfile, join

class facebookReader(object):

    def __init__(self, page_id, app_id, app_secret):
        self.page_id = page_id
        self.access_token = app_id + "|" + app_secret
    
    def request_until_succeed(self, url):
        req = urllib2.Request(url)

        permission_error_count = 0

        success = False
        while success is False:
            try: 
                response = urllib2.urlopen(req)
                if response.getcode() == 200:
                    success = True
            except Exception, e:
                print e

                error = json.loads(e.read())
                error_message = error["error"]["message"]
                if "cannot be loaded due to missing permissions" in error_message:
                    permission_error_count += 1

                if "was migrated to page ID" in error_message:
                    raise Exception("PAGE MIGRATED ERROR", error_message)

                if permission_error_count > 3:
                    raise Exception('PERMISSION ERROR')


                time.sleep(5)
                
                print "Error for URL %s: %s" % (url, datetime.datetime.now())
                print "Retrying."

        return response.read()


    # Needed to write tricky unicode correctly to csv
    def unicode_normalize(self, text):
        return text.translate({ 0x2018:0x27, 0x2019:0x27, 0x201C:0x22, 0x201D:0x22, 0xa0:0x20 }).encode('utf-8')

    def getFacebookPageFeedData(self, num_statuses):
        page_id = self.page_id
        access_token = self.access_token
        
        # Construct the URL string; see http://stackoverflow.com/a/37239851 for Reactions parameters
        base = "https://graph.facebook.com/v2.11"
        node = "/%s/posts" % page_id 
        fields = "/?fields=message,link,created_time,type,name,id,comments.limit(0).summary(true),shares,reactions.limit(0).summary(true)"
        date_info = "&since=" + "2016-01-01" #only need since reactions published Feb 26, 2016
        parameters = "&limit=%s&access_token=%s" % (num_statuses, access_token)
        url = base + node + fields + date_info + parameters
        
        # retrieve data
        try:
            data = json.loads(self.request_until_succeed(url))
        except Exception as e:
            raise Exception(e)

        return data

    def getFacebookPlaceData(self, center, distance):
        page_id = self.page_id
        access_token = self.access_token
        
        # Construct the URL string; see https://developers.facebook.com/docs/places/fields for fields parameters
        base = "https://graph.facebook.com/v2.11"
        node = "/search?type=place&center=%s&distance=%s" % (center, distance)
        fields = "&fields=name,checkins,picture,category_list,description,engagement,location,overall_star_rating,rating_count,single_line_address,website"
        parameters = "&access_token=%s" % (access_token)
        url = base + node + fields + parameters
        
        # retrieve data
        data = json.loads(self.request_until_succeed(url))
        
        return data
        
    def getReactionsForStatus(self, status_id):
        access_token = self.access_token

        # See http://stackoverflow.com/a/37239851 for Reactions parameters
        # Reactions are only accessable at a single-post endpoint
        
        base = "https://graph.facebook.com/v2.11"
        node = "/%s" % status_id
        reactions = "/?fields=" \
                        "reactions.type(LIKE).limit(0).summary(total_count).as(like)" \
                        ",reactions.type(LOVE).limit(0).summary(total_count).as(love)" \
                        ",reactions.type(WOW).limit(0).summary(total_count).as(wow)" \
                        ",reactions.type(HAHA).limit(0).summary(total_count).as(haha)" \
                        ",reactions.type(SAD).limit(0).summary(total_count).as(sad)" \
                        ",reactions.type(ANGRY).limit(0).summary(total_count).as(angry)"
        parameters = "&access_token=%s" % access_token
        url = base + node + reactions + parameters
        
        # retrieve data
        try:
            data = json.loads(self.request_until_succeed(url))
        except:
            raise Exception('PERMISSION ERROR')
        
        return data

    def writeUsersToFile(self, filename, status_id, interaction_type, user_id, user_name, additional_info_list):
        f = open(filename, 'ab')
        w = csv.writer(f)
        w.writerow([status_id, interaction_type, user_id, user_name] + additional_info_list)
        f.close()


    def getUsers(self, status_id):
        page_id = self.page_id
        access_token = self.access_token

        #interaction_modes = ["likes", "comments"]
        interaction_modes = ["comments"]
        for interaction in interaction_modes: #sharedposts - need to have Luvo grant my app access to be able to get these
            base = "https://graph.facebook.com/v2.11"
            node = "/%s" % status_id
            parameters = "/" + interaction
            reactions = "/?fields=" \
                        "reactions.type(LIKE).limit(0).summary(total_count).as(like)" \
                        ",reactions.type(LOVE).limit(0).summary(total_count).as(love)" \
                        ",reactions.type(WOW).limit(0).summary(total_count).as(wow)" \
                        ",reactions.type(HAHA).limit(0).summary(total_count).as(haha)" \
                        ",reactions.type(SAD).limit(0).summary(total_count).as(sad)" \
                        ",reactions.type(ANGRY).limit(0).summary(total_count).as(angry)"
            basic_info = ",created_time,message,parent,from"
            access_token = "&access_token=%s" % access_token
            url = base + node + parameters + reactions + basic_info + access_token



            has_next_page = True
            users = json.loads(self.request_until_succeed(url))

            while has_next_page:
                for user in users['data']:
                
                    # Ensure it is a status with the expected metadata
                    if interaction == "likes":# and 'name' in user:
                        #user_id = user["id"]
                        user_id = user.get("id", "")
                        #user_name = self.unicode_normalize(user["name"])
                        #user_name = user["name"]
                        user_name = user.get("name")
                        message = "" #no comment text if it's a like
                        self.writeUsersToFile("data/" + page_id + "_facebook_users_interactions.csv", status_id, interaction, user_id, user_name, [message])
                    if interaction == "comments":# and 'from' in user:
                        #user_id = user["from"]["id"]
                        user_id = user.get("from", {}).get("id", "")
                        #user_name = self.unicode_normalize(user["from"]["name"])
                        #user_name = user["from"]["name"]
                        user_name = user.get("from", {}).get("name", "")
                        #message = self.unicode_normalize(user["message"]).replace("\n", " ")
                        #message = user["message"].replace("\n", " ")
                        message = user.get("message", "").replace("\n", " ")

                        parent_comment_id = user.get("parent", {}).get("id", "")
                        #get additional infor about the comment here
                        comment_id, comment_message, link_name, comment_type, comment_link, comment_published, num_reactions, num_comments, num_shares, num_likes, num_loves, num_wows, num_hahas, num_sads, num_angrys = self.processFacebookPageFeedStatus(user)
                        self.writeUsersToFile("data/" + page_id + "_facebook_users_interactions.csv", status_id, interaction, user_id, user_name, [comment_id, comment_message, parent_comment_id, link_name, comment_type, comment_link, comment_published, num_reactions, num_comments, num_shares, num_likes, num_loves, num_wows, num_hahas, num_sads, num_angrys])
                        
                # if there is no next page, we're done.
                if 'paging' in users.keys() and 'next' in users['paging'].keys():
                    users = json.loads(self.request_until_succeed(users['paging']['next']))
                else:
                    has_next_page = False

    def processFacebookPageFeedStatus(self, status):
        access_token = self.access_token
        
        # The status is now a Python dictionary, so for top-level items,
        # we can simply call the key.
        
        # Additionally, some items may not always exist,
        # so must check for existence first
        
        status_id = status['id']
        #status_message = '' if 'message' not in status.keys() else self.unicode_normalize(status['message']).replace("\n", " ")
        status_message = '' if 'message' not in status.keys() else status['message'].replace("\n", " ")
        #link_name = '' if 'name' not in status.keys() else self.unicode_normalize(status['name'])
        link_name = '' if 'name' not in status.keys() else status['name']
        status_type = '' if 'type' not in status.keys() else status['type']
        #status_link = '' if 'link' not in status.keys() else self.unicode_normalize(status['link'])
        status_link = '' if 'link' not in status.keys() else status['link']
        
        # Time needs special care since a) it's in UTC and
        # b) it's not easy to use in statistical programs.
        
        status_published = datetime.datetime.strptime(status['created_time'],'%Y-%m-%dT%H:%M:%S+0000')
        #status_published = status_published + datetime.timedelta(hours=-7) # PST
        status_published = status_published.strftime('%Y-%m-%d %H:%M:%S') # best time format for spreadsheet programs
        
        # Nested items require chaining dictionary keys.
        
        num_reactions = 0 if 'reactions' not in status else status['reactions']['summary']['total_count']
        num_comments = 0 if 'comments' not in status else status['comments']['summary']['total_count']
        num_shares = 0 if 'shares' not in status else status['shares']['count']

        #get the users that have reacted/commented on the facebook status
        #self.getUsers(status_id) #####Commenting this out for now so that we only get statuses
        
        # Counts of each reaction separately; good for sentiment
        # Only check for reactions if past date of implementation: http://newsroom.fb.com/news/2016/02/reactions-now-available-globally/
        
        try:
            reactions = self.getReactionsForStatus(status_id) if status_published > '2016-02-24 00:00:00' else {}
        except:
            return (status_id, status_message, link_name, status_type, status_link,
                   status_published, num_reactions, num_comments, num_shares, "ERROR",
                   "ERROR", "ERROR", "ERROR", "ERROR", "ERROR")
        
        num_likes = 0 if 'like' not in reactions else reactions['like']['summary']['total_count']
        
        # Special case: Set number of Likes to Number of reactions for pre-reaction statuses
        
        num_likes = num_reactions if status_published < '2016-02-24 00:00:00' else num_likes
        
        num_loves = 0 if 'love' not in reactions else reactions['love']['summary']['total_count']
        num_wows = 0 if 'wow' not in reactions else reactions['wow']['summary']['total_count']
        num_hahas = 0 if 'haha' not in reactions else reactions['haha']['summary']['total_count']
        num_sads = 0 if 'sad' not in reactions else reactions['sad']['summary']['total_count']
        num_angrys = 0 if 'angry' not in reactions else reactions['angry']['summary']['total_count']
        
        # Return a tuple of all processed data
        
        return (status_id, status_message, link_name, status_type, status_link,
               status_published, num_reactions, num_comments, num_shares,  num_likes,
               num_loves, num_wows, num_hahas, num_sads, num_angrys)

    def scrapeFacebookPageFeedStatus(self):
        page_id = self.page_id
        acess_token = self.access_token

        #initialize user_interactions csv file
        f = open("data/" + page_id + "_facebook_users_interactions.csv", 'wb')
        w = csv.writer(f)
        w.writerow(["status_id", "interaction_type", "user_id", "user_name", "comment_id", 
                    "comment_message", "parent_comment_id", "link_name", "comment_type", "comment_link", "comment_published", 
                    "num_reactions", "num_comments", "num_shares", "num_likes", "num_loves", "num_wows", 
                    "num_hahas", "num_sads", "num_angrys"])
        f.close()

        with open('data/%s_facebook_statuses.csv' % page_id, 'wb') as file:
            w = csv.writer(file)
            w.writerow(["status_id", "status_message", "link_name", "status_type", "status_link",
               "status_published", "num_reactions", "num_comments", "num_shares", "num_likes",
               "num_loves", "num_wows", "num_hahas", "num_sads", "num_angrys"])
            
            has_next_page = True
            num_processed = 0   # keep a count on how many we've processed
            scrape_starttime = datetime.datetime.now()
            
            print "Scraping %s Facebook Page: %s\n" % (page_id, scrape_starttime)
            
            try:
                statuses = self.getFacebookPageFeedData(100) #100 is max you can request at a time
            except Exception as e:
                f = open("pages_to_recheck.csv", 'a')

                if str(e[0]) == "PAGE MIGRATED ERROR":
                    print "NEED TO RECHECK " + str(e[1])
                    f.write(e[1] + "\n")
                else:
                    print "NEED TO RECHECK " + str(page_id)
                    f.write(page_id + "\n")

                f.close()
                has_next_page = False

            
            while has_next_page:
                for status in statuses['data']:
                
                    # Ensure it is a status with the expected metadata
                    if 'reactions' in status:
                        w.writerow(self.processFacebookPageFeedStatus(status))
                    
                    # output progress occasionally to make sure code is not stalling
                    num_processed += 1
                    if num_processed % 10 == 0:
                        print "%s Statuses Processed: %s" % (num_processed, datetime.datetime.now())
                        
                # if there is no next page, we're done.
                if 'paging' in statuses.keys() and 'next' in statuses['paging'].keys():
                    statuses = json.loads(self.request_until_succeed(statuses['paging']['next']))
                else:
                    has_next_page = False
                    
            
            print "\nDone!\n%s Statuses Processed in %s" % (num_processed, datetime.datetime.now() - scrape_starttime)


    def processFacebookPlaceInfo(self, place):
        
        # The status is now a Python dictionary, so for top-level items,
        # we can simply call the key.
        
        # Additionally, some items may not always exist,
        # so must check for existence first
        
        place_id = place['id']
        #name = self.unicode_normalize(place['name'])
        name = place['name']
        checkin_count = place['checkins']
        #picture_url = self.unicode_normalize(place['picture']['data']['url'])
        picture_url = place['picture']['data']['url']
        categories = "|".join([category['name'] for category in place['category_list']]) #can also have unicode when non-US
        #description = "" if 'description' not in place else self.unicode_normalize(place['description'])
        description = "" if 'description' not in place else place['description']
        place_likes = place['engagement']['count']
        #location_address = "" if 'single_line_address' not in place else self.unicode_normalize(place['single_line_address'])
        location_address = "" if 'single_line_address' not in place else place['single_line_address']
        location_lat = place['location']['latitude']
        location_long = place['location']['longitude']
        rating_value = "" if 'overall_star_rating' not in place else place['overall_star_rating']
        rating_count = place['rating_count']
        #website = "" if 'website' not in place else self.unicode_normalize(place['website'])
        website = "" if 'website' not in place else place['website']

        
        # Return a tuple of all processed data
        return (place_id, name, checkin_count, picture_url, categories, description, place_likes,
               location_address, location_lat, location_long, rating_value, rating_count, website)


    def scrapeFacebookPlaces(self, center, distance, location):
        page_id = self.page_id
        acess_token = self.access_token

        with open('data/%s_facebook_places.csv' % location, 'wb') as file:
            w = csv.writer(file)
            w.writerow(["place_id", "name", "checkin_count", "picture_url", "categories", "description",
               "place_likes", "location_address", "location_lat", "location_long", "rating_value",
               "rating_count", "website"])
            
            has_next_page = True
            num_processed = 0   # keep a count on how many we've processed
            scrape_starttime = datetime.datetime.now()
            
            print "Scraping %s Facebook Places: %s\n" % (location, scrape_starttime)
            
            places = self.getFacebookPlaceData(center, distance)
            
            while has_next_page:
                for place in places['data']:
                
                    # Ensure it is a place with the expected metadata
                    if 'name' in place:
                        w.writerow(self.processFacebookPlaceInfo(place))
                    
                    # output progress occasionally to make sure code is not stalling
                    num_processed += 1
                    if num_processed % 10 == 0:
                        print "%s Places Processed: %s" % (num_processed, datetime.datetime.now())
                        
                # if there is no next page, we're done.
                if 'paging' in places.keys() and 'next' in places['paging'].keys():
                    places = json.loads(self.request_until_succeed(places['paging']['next']))
                else:
                    has_next_page = False
                    
            
            print "\nDone!\n%s Places Processed in %s" % (num_processed, datetime.datetime.now() - scrape_starttime)




if __name__ == "__main__":
    app_id = ""
    app_secret = ""
    page_id = "humansofnewyork" #can also just specify the page to scrape

    test = facebookReader(page_id, app_id, app_secret)


    #to get Lincoln posts
    #center = "40.805755,-96.682561"
    #distance = "13000" #distance in meters
    #location = "lincolnNE"

    #to get all posts in US
    #read in json file of top 1000 cities in US, from here: https://gist.github.com/Miserlou/c5cd8364bf9b2420bb29
    """city_data = json.load(open("cities_top_1000.json"))
    for entry in city_data:
        city = entry["city"].replace("/", "-")
        state = entry["state"]

        lat = entry["latitude"]
        lon = entry["longitude"]

        center = str(lat) + "," + str(lon)
        distance = "50000" #max distance is 50km (50,000 meters)
        location = city + "_" + state

        test.scrapeFacebookPlaces(center, distance, location) #outputs one csv file: location_facebook_places.csv"""

    #for each of the places in the US, get all statuses of the places
    count = 0
    mypath = "data/"
    onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]
    for f in onlyfiles:
        if "facebook_places" in f:
            location_file = open(mypath + f, 'r')
            csv_reader = csv.reader(location_file, delimiter=',', quotechar='"')

            csv_reader.next() #skip header

            for row in csv_reader:
                place_id = row[0]


                onlyfiles_new = [f_new for f_new in listdir(mypath) if isfile(join(mypath, f_new))]


                #145022228864377 51189044844 should error handle message:
                """{
                   "error": {
                      "message": "(#2) Service temporarily unavailable",
                      "type": "OAuthException",
                      "is_transient": true,
                      "code": 2,
                      "fbtrace_id": "HMKnDpxYmal"
                   }
                }""" #119531358091471, 142676649096880 41585566807 ##### COME BACK AND CHECK THIS ONE, LAST PAGING DOES NOT HAVE NEXT
                #if place_id not in ["145022228864377"]: #the ones that error/are no longer active?? should have better handling for this
                #update: now the above seems to work. will need to rerun it later

                #####WILL NEED TO MODIFY GET USERS NOW THAT FACEBOOK NO LONGER RETURNS THE USER ID :(

                #do not want to rescrape one already done ####32407 is PID
                if not place_id + "_facebook_statuses.csv" in onlyfiles_new:

                    #categories = row[4].lower()
                    #if "city" in categories or "government" in categories: #only get city/government related ones
                    count += 1
                    print "DONE", count, "TOTAL", 12362, float(count)/12362*100

                    test = facebookReader(place_id, app_id, app_secret)
                    test.scrapeFacebookPageFeedStatus() #outputs two csv files: company_facebook_statuses.csv and company_facebook_users_interactions.csv
                

    #failed attempt at getting all of US, max distance is 50km
    #center = "39.8283,-98.5795"
    #distance = "3000000"
    #location = "center_of_US"

    #test = facebookReader(page_id, app_id, app_secret)

    #if just wanting one page
    #test.scrapeFacebookPageFeedStatus() #outputs two csv files: company_facebook_statuses.csv and company_facebook_users_interactions.csv

    ######NEED TO MOVE BACK TO ORIGINAL LOCATION OR AT LEAST KEEP A CONSISTENT VERSION, probably push to the lincoln github?
    ######POSSIBLE THE WHOLE THING IS IN PST. should no longer be
    #should recomment self.getUsers(status_id) when want to get info about user interactions
    
    #scrape place info
    #test.scrapeFacebookPlaces(center, distance, location) #outputs one csv file: location_facebook_places.csv

    
    #for each place, scrape statuses on it and user comments
    """location_file = open('data/%s_facebook_places.csv' % location, 'r')
    csv_reader = csv.reader(location_file, delimiter=',', quotechar='"')

    csv_reader.next() #skip header
    for i in range(206):
        csv_reader.next() #skip 207 rows since that's where we left off before it errored

    for row in csv_reader:
        place_id = row[0]

        test = facebookReader(place_id, app_id, app_secret)
        test.scrapeFacebookPageFeedStatus() #outputs two csv files: company_facebook_statuses.csv and company_facebook_users_interactions.csv
    """