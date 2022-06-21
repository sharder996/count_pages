#!/usr/bin/python3

############################################################################
#
# obi-2.x:	bigramを用いた日本語テキストの難易度推定
#
#
#  Copyright (c) Satoshi Sato, 2009.
#  License: Creative Commons 3.0, Attribution-Noncommercial-Share Alike.
#
############################################################################

import re

from calibre_plugins.count_pages.nltk_lite.obi2 import regression

KCODE = 'utf8'

Version = 'obi2.305 (2009-08-12)'


op_char_file = './jchar.utf8'
model_file = './Obi2-T13.model'


class Result:
	MethodList = ['ns', 's5', 's4', 's3', 's2']
	VotingList = ['ns', 's4', 's2']

	def __init__(self, text, contrib):
		self.text = text
		self.contrib = contrib
		self.estimate = self.make_estimation(self.contrib)
		self.final = self.final_estimation(self.estimate)

	def make_estimation(self, contrib: list) -> dict:
		estimat = dict()

		operative_len = contrib[0]
		if operative_len > 0:
			estimat['ns'] = [100 * contrib[i] / operative_len for i in range(1, len(contrib))]
			for i in range(2, 6):
				estimat[f's{i}'] = regression.regression(i, estimat['ns'], None)
		return estimat

	def final_estimation(self, estimat: dict) -> list:
		if len(estimat) > 0:
			list = [estimat[x].index(max(estimat[x]))+1 for x in self.MethodList]
			temp = sorted([estimat[x].index(max(estimat[x]))+1 for x in self.VotingList])
			return [temp[int(len(temp)/2)]] + list if int(len(temp)) % 2 != 0 \
				else [(temp[int(len(temp)/2-1)] + temp[int(len(temp)/2)]) / 2] + list
		else:
			return [0] * len(self.MethodList)


class Model:
	def __init__(self, model):
		self.model = model

	def readability(self, text, op_char):
		parsed_text = load_text(text, op_char)
		return Result(parsed_text, self.calculate_likelihoods(parsed_text))

	def calculate_likelihoods(self, text):
		total = [0]
		for key in list(text.keys()):
			if key in self.model:
				total[0] += text[key][0]
				for i in range(1, len(self.model[key])):
					if len(total) <= i:
						total.append(0.0)
					if len(text[key]) <= i:
						text[key].append(0.0)
					text[key][i] = text[key][0] * self.model[key][i]
					total[i] += text[key][i]
			else:
				del text[key]  # Not a valid bigram!
		return total


class Obi2(object):
	def __init__(self, obi2_resources):
		self.op_char = load_operative_character_file(obi2_resources['nltk_lite/obi2/jchar.utf8'].decode('utf-8'))
		self.model = load_model_file(obi2_resources['nltk_lite/obi2/Obi2-T13.model'].decode('utf-8'))

	def analyze_text(self, text=''):
		return self.model.readability(text, self.op_char).final[0]


def load_operative_character_file(file):
	"""
	Load valid character definition file/check valid bigram
	"""
	operative = dict()
	# with open(filename, 'r', encoding='utf-8') as f:
	for line in file.split('\n'):
		operative[line.strip('\r\n').split('\t')[0]] = True
	return operative


def load_model_file(file):
	model = dict()
	# with open(filename, 'r', encoding='utf-8') as f:
	for line in file.split('\n'):
		if len(line) > 0:
			x = line.strip('\r\n').split('\t')
			if int(x[1]) >= 1:
				key = x.pop(0)
				model[key] = [int(x.pop(0))] + [float(v) for v in x]
	return Model(model)


def load_text(text, op_char):
	"""
	Load text
	"""
	parsed_text = dict()

	for b in operative_ngram_from_io(text, op_char):
		if b not in parsed_text:
			parsed_text[b] = [0]
		parsed_text[b][0] += 1

	return parsed_text


def operative_ngram_from_io(text, op_char):
	"""
	n-gram
	"""
	for b in bigram_from_io(text):
		if is_operative(b, op_char):
			yield b


def bigram_from_io(text):
	"""
	Get bigram
	"""
	c = list()
	for line in text:
		line = line.strip('\r\n')

		if re.search(r'^\s*$', line) or re.search(r'^<', line):  # If line is whitespace or a tag, do not continue the line
			c = list()

		# Format text
		tail_tag = re.search(r'>$', line)
		line = re.sub(r'<[^<]*>', '', line)
		line = re.sub(r'\s', '', line)

		# Create bigram
		c += list(line)
		for _ in range(len(c)-1):
			b = ''.join(c[0:2])
			yield b
			c.pop(0)

		if tail_tag:  # If the end of a line is a tag, terminate the line
			c = list()


def is_operative(bigram, operative):
	for c in list(bigram):
		if c not in operative:
			return False
	return True
