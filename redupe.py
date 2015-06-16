from geopy.distance import vincenty
from sets import Set
from colorama import Fore
from fuzzywuzzy import fuzz
import dedupe
import re
import sys, traceback
import yaml
import argparse
import curses





class redupe:
	def __init__(self, i_ruleset, i_file, manual = False):
		
		self.mapping = {}
		self.data, self.ruleset = {}, []

		with open(i_ruleset, "rb") as r:
			for rule in yaml.safe_load_all(r):
				self.ruleset.append(rule)
		self.get_data(i_file)
		
		if not manual:

			self.deduper = dedupe.Dedupe(self.ruleset[0]['variables'])
			self.read()

	def concat(self, input):
		addr = input['address']
		city = input['city']
		state = input['state']
		zipper = input['zip']
		return ('%s, %s, %s %s' % (addr, city, state, zipper))

	def compare(self, tup):
		r_comm = fuzz.token_set_ratio(tup[1][0]['community'].lower(), tup[1][1]['community'].lower())
		r_addr = fuzz.token_set_ratio(self.concat(tup[1][0]).lower(), self.concat(tup[1][1]).lower())
		comp = False
		if r_comm >= 95 or r_addr >= 95:
			comp = True

		elif (r_comm >= 50 or r_addr >= 50) and (tup[1][0]['geocode'] != (0.0, 0.0) and tup[1][1]['geocode'] != (0.0, 0.0)):

			distance = vincenty(tup[1][0]['geocode'], tup[1][1]['geocode']).miles
			if distance <= 0.4:
				comp = True

		if comp:
			if self.mapping.has_key(tup[0][0]):
				self.mapping[tup[0][1]] = self.mapping[tup[0][0]]
			else:
				self.mapping[tup[0][0]] = tup[0][0]
				self.mapping[tup[0][1]] = tup[0][0]

	def danny_dedupes(self):
		num = len(self.data)
		for i in xrange(0, num):
			sys.stderr.write("Working on: %s of %s\n" % (i + 1, num))
			for j in xrange(i + 1, num):
				tup = ((i, j),(self.data[i], self.data[j]))
				self.compare(tup)


	def normalize(self, i_str):

		temp = re.sub(self.ruleset[0]['remove'], '', i_str)
		out = re.split("\s+", temp)
		for i, word in enumerate(out):
			if self.ruleset[0]['replace'].has_key(word.lower()):
				out[i] = self.ruleset[0]['replace'][word.lower()]

		return " ".join(out)


	def get_data(self, i_file):
		properties = []
		with open(i_file, 'rb') as f:
			lines, cleaner = f.readlines()[1:], []
			for line in lines:
				line = re.sub('\n(?=\t)', '', line)
				line = re.sub('(\t)?_x000D_(\n)?', '', line)
				line = re.sub('\n{2,}', '', line)
				cleaner.append(line)
			conjoined = "".join(cleaner)
			
			for line in conjoined.split("\n"):
				if len(line) > 0:
					cells = re.split('\t', line)
					try:
						lat = lon = 0.0
						try:
							lat = float(cells[6])
							lon = float(cells[7])
						except:
							pass
						prop = 	{
									'community': self.normalize(cells[0]).encode('ascii'),
									'address': self.normalize(cells[1]).encode('ascii'),
									'city': cells[2].encode('ascii'),
									'state': cells[3].encode('ascii'),
									'zip': cells[4].encode('ascii'),
									'geocode': (lat, lon) 
								}
						properties.append(prop)
					except Exception as inst:
						sys.stderr.write(Fore.RED + "%s, %s, %s\n" % (sys.exc_info()[0], inst, inst.args) + Fore.RESET)
						traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2])
					
				else:
					continue
		for i, prop in enumerate(properties):
			self.data[i] = prop
		



	def run(self):
		
		data_sample = self.deduper.sample(self.data)
		
		
		

	def read(self):
		try:
			with open('./.training.json', 'rb') as f:
				self.deduper.readTraining(f)
		except:
			sys.stderr.write("Training File Not Found.\n")


	def write(self):
		try:
			with open('./.training.json', 'wb') as f:
				self.deduper.writeTraining(f)
			with open('./.settings', 'wb') as f:
				self.deduper.writeSettings(f)

		except Exception as inst:
			sys.stderr.write(str(inst) + "\n")

def main():
	

	parser = argparse.ArgumentParser(description="Deduplicate a list of properties.")

	parser.add_argument('-t', '--train',
		action='store_true',
		help='run the training program to more accurately remove duplicates')

	parser.add_argument('-m', '--manual',
		action='store_true',
		help='run a rule-based version of redupe not based on dedupe/machine learning',
		default=False)

	parser.add_argument('-a', '--auto',
		action='store_true',
		help='run the automatic training function after enough training data is stored')

	parser.add_argument('infile', 
		nargs='?',
		type=str)

	parser.add_argument('outfile',
		nargs='?',
		type=argparse.FileType('w'),
		default=sys.stdout)


	args = parser.parse_args()

	remove = redupe("ruleset.yaml", args.infile, args.manual)


	if not args.manual:
		remove.run()

	if args.manual:
		remove.danny_dedupes()
		flag = ''
		for i in xrange(0, len(remove.data.keys())):
			if remove.mapping.has_key(i):
				w_item = remove.data[remove.mapping[i]]
				flag = "\t%s" % str(remove.mapping[i] + 1)
			else:
				w_item = remove.data[i]
				
			args.outfile.write("%s\t%s%s\n" % (remove.concat(remove.data[i]), remove.concat(w_item), flag))
			flag = ''

	elif args.auto:
		remove.deduper.train()
		remove.write()



	elif args.train:
		stdscr = curses.initscr()

		curses.noecho()

		curses.cbreak()

		stdscr.keypad(1)
		group = remove.deduper.uncertainPairs()

		while True:

			try:
				active = group[0]
			except:
				group = remove.deduper.uncertainPairs()
				if len(group) == 0:
					stdscr.clear()
					stdscr.addstr("No Uncertain Pairs\n")
					active = None
				else:
					active = group[0]
			if active != None:
				for key in active[0].keys():
					stdscr.addstr("%s -> \t%s : \t%s\n" % (key, active[0][key], active[1][key]))
				stdscr.addstr("Distance: %sm" % vincenty(active[0]['geocode'], active[1]['geocode']).meters)

			c = stdscr.getch()

			if c == ord('1') and active != None:
				
				stdscr.clear()
				group.pop(0)
				example = {	'match' : [active],
							'distinct' : []}
				remove.deduper.markPairs(example)

			elif c == ord('0') and active != None:
				stdscr.clear()
				group.pop(0)
				example = {	'match' : [],
							'distinct' : [active]}
				remove.deduper.markPairs(example)

			elif c == ord('q'):

				remove.write()
				curses.nocbreak(); stdscr.keypad(0); curses.echo()

				curses.endwin()
				break

	else:
		with open('./.settings', 'rb') as f:
			deduper = dedupe.StaticDedupe(f)


		threshold = deduper.threshold(remove.data, recall_weight=2)
		duplicates = deduper.match(remove.data, threshold)

		d_map = {}
		for item in duplicates:
			indices = Set(item[0])
			for i in xrange(0, len(indices)):
				g_indices = indices - Set([item[0][i]])
				out = ''
				for g in g_indices: out += ("%s: %s " % (g, remove.data[g]['community']))
				d_map[item[0][i]] = {'conf': item[1][i], 'group': out}


		for i in xrange(0, len(remove.data.keys())):
			address = remove.data[i]['address']
			city = remove.data[i]['city']
			state = remove.data[i]['state']
			zipper = remove.data[i]['zip']
			comm = remove.data[i]['community']
			f_address = "%s, %s, %s %s" % (address, city, state, zipper)

			if d_map.has_key(i):
				args.outfile.write("%s\t%s\t%s\t%s\n" % (comm, f_address, d_map[i]['conf'], d_map[i]['group']))
			else:

				args.outfile.write("%s\t%s\n" % (comm, f_address))
		"""
		for item in duplicates:
			for i in xrange(0, len(item[0])):
				print item[1][i], remove.data[item[0][i]]
			print "\n\n------------------------------------\n\n" 
		"""

main()