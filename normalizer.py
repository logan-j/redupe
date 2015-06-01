from geopy.geocoders import Bing
from multiprocessing import Pool
import glob
import time

def main(i_file):
	output = []
	geolocator = Bing("AtcC6StvDvg1Wjzd8nM2_DnjF6Mtt3Vqh4vYQliQWOsULURUo4lo2EcsXkM8zSdJ")

	with open(i_file, 'r') as f:
		for line in f.readlines():
			location = None
			try:
				attempt = str(line.split("\t")[5])
				print attempt
				time.sleep(0.25)
				location =  geolocator.geocode(attempt)
			except:
				print "FAILED"

			if location != None:
				output.append("%s\t%s" % (location.latitude, location.longitude))
			else:
				output.append('')
	with open("g_" + i_file, 'w') as f:
		for item in output:
			f.write(item + "\n")	

files = glob.glob("n_samples/N_E_*.csv")


pool = Pool(4)

pool.map(main, files)
