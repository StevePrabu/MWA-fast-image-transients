import urllib
import urllib2
import json
import sys

import sqlite3

__author__ = "PaulHancock"

# Append the service name to this base URL, eg 'con', 'obs', etc.
BASEURL = 'http://mwa-metadata01.pawsey.org.au/metadata/'
dbfile = 'MWA-GRB.sqlite'


# Function to call a JSON web service and return a dictionary: This function by Andrew Williams
def getmeta(service='obs', params=None):
    """
    Given a JSON web service ('obs', find, or 'con') and a set of parameters as
    a Python dictionary, return a Python dictionary containing the result.
    """
    if params:
        data = urllib.urlencode(params)  # Turn the dictionary into a string with encoded 'name=value' pairs
    else:
        data = ''
    # Validate the service name
    if service.strip().lower() in ['obs', 'find', 'con']:
        service = service.strip().lower()
    else:
        print "invalid service name: %s" % service
        return
    # Get the data
    try:
        print BASEURL + service + '?' + data
        result = json.load(urllib2.urlopen(BASEURL + service + '?' + data))
    except urllib2.HTTPError as error:
        print "HTTP error from server: code=%d, response:\n %s" % (error.code, error.read())
        return
    except urllib2.URLError as error:
        print "URL or network error: %s" % error.reason
        return
    # Return the result dictionary
    return result


def update_observation(obsid, obsname, cur):
    if 'CORR_MODE' in obsname:
        return
    elif 'GRB' in obsname:
        # eg GRB467353077_145
        idx = obsname[3:-4]
    elif 'GCN' in obsname:
        idx = obsname[3:]
    else:
        idx = obsname
    cur.execute("SELECT count(name) FROM grb WHERE fermi_trigger_id = ?", (idx,))
    if cur.fetchone()[0] > 0:
        cur.execute("SELECT name FROM grb WHERE fermi_trigger_id = ?", (idx,))
        grb = cur.fetchone()[0]
        cur.execute("UPDATE observation SET grb = ? WHERE obs_id =?", (grb, obsid))
    return


def copy_obs_info(obsid, cur):
    cur.execute("SELECT count(*) FROM observation WHERE obs_id =?",(obsid,))
    if cur.fetchone()[0] > 0:
        print "already imported", obsid
        return
    meta = getmeta(service='obs', params={'obs_id':obsid})
    if meta is None:
        print obsid, "has no metadata!"
        return
    metadata = meta['metadata']
    cur.execute("""
    INSERT OR REPLACE INTO observation
    (obs_id, projectid,  lst_deg, starttime, duration_sec, obsname, creator,
    azimuth_pointing, elevation_pointing, ra_pointing, dec_pointing,
    freq_res, int_time, grb,
    calibration, cal_obs_id, calibrators, nfiles,
    archived
    )
    VALUES (?,?,?,?,?, ?,?,?,?,?, ?,?,?,?,?, ?,?,?,?);
    """, (
    obsid, meta['projectid'], metadata['local_sidereal_time_deg'], meta['starttime'], meta['stoptime']-meta['starttime'], meta['obsname'], meta['creator'],
    metadata['azimuth_pointing'], metadata['elevation_pointing'], metadata['ra_pointing'], metadata['dec_pointing'],
    meta['freq_res'], meta['int_time'], None,
    metadata['calibration'], None, metadata['calibrators'], len(meta['files']), False))
    update_observation(obsid, meta['obsname'], cur)
    return


def update_grb_links(cur):
    # associate each observation with the corresponding grb
    cur.execute("SELECT obs_id, obsname FROM observation WHERE grb IS NULL")
    # need to do this to exhaust the generator so we can reuse the cursor
    obsids, obsnames = zip(*cur.fetchall())
    for obsid, obsname in zip(obsids, obsnames):
        update_observation(obsid, obsname, cur)

    # now associate each calibration observation with a grb
    # this relies on the calibration observation being within 150sec of the regular obs
    cur.execute("""
    SELECT o.obs_id, b.grb
    FROM observation o JOIN observation b ON
    o.obs_id - b.obs_id BETWEEN -150 AND 150
    AND o.calibration AND b.grb IS NOT NULL
    AND o.obs_id != b.obs_id
    """)
    ids, grbs = zip(*cur.fetchall())
    for idx, grb in zip(ids, grbs):
        cur.execute("UPDATE observation SET grb=? WHERE obs_id=?", (grb, idx))
    return


if __name__ == "__main__":
    ids = []
    for a in sys.argv:
        try:
            ids.append(int(a))
        except ValueError as e:
            pass
    conn = sqlite3.connect(dbfile)
    cur = conn.cursor()

    if len(ids) > 0:
        for obs_id in ids:
            copy_obs_info(obs_id,cur)
            conn.commit()
        sys.exit()
    #obsdata = getmeta(service='find', params={'projectid':'D0009', 'limit':100000}) #'limit':10
    obsdata = getmeta(service='find', params={'creator':'mwagrb.py', 'limit':100000}) #'limit':10
    # For Jai's project - MAXI J1535 - XRB
    #obsdata = getmeta(service='find', params={'obsname':'J1535_%', 'limit':100000}) #'limit':10
    # For Jai's project - MAXI J1820 - XRB
    #obsdata = getmeta(service='find', params={'obsname':'J1820_%', 'limit':100000}) #'limit':10
    for obs in obsdata:
        obs_id = obs[0]
        copy_obs_info(obs_id, cur)
        conn.commit()
    update_grb_links(cur)
    conn.commit()
    conn.close()
