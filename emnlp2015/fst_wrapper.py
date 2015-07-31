#!/usr/bin/python
# -*- coding: utf-8 -*-
# Author: Beat Kunz

from __future__ import unicode_literals, print_function
import sys
import re
import pexpect


class FstWrapper():
    def __init__(self, smor_binary, smor_model):
        self.child = pexpect.spawnu(smor_binary + ' ' + smor_model)
        self.child.delaybeforesend = 0
        self.child.expect(["analyze> ", pexpect.EOF], timeout=600)
        self.morAnalyseMode = True
        before = self.child.before
        if self.child.terminated:
            raise RuntimeError(before)

    def analyse(self, word):
        word = word.strip()
        if word == "" or word == "q" or word == "\x7f":
            return []
        # if not in analyse mode, go to it
        if self.morAnalyseMode == False: 
            # print "Was not in analyse mode => toggle to it!"
            self.toggleMorMode()
            self.child.sendline("") # "" is used in the fst-mor to toggle between analyse/generate
            self.child.expect(["analyze> ", pexpect.EOF])
            self.child.before
        self.child.sendline(word)
        try:
            self.child.expect(["analyze> ", pexpect.EOF])
        except pexpect.TIMEOUT:
            sys.stderr.write('Warning: timeout while waiting for fst-mor\n')
            sys.stderr.write('String: {0}'.format(word))
            return []
        result = self.child.before.split("\r\n")[1:-1]
        if len(result) == 1 and re.match("^no result for ", result[0]):
            result = []
        return result

    def generate(self, word):
        word = word.strip()
        if word == "" or word == "q":
            return []
        # if not in analyse mode, go to it
        if self.morAnalyseMode == True: 
            # print "Was not in generate mode => toggle to it!"
            self.toggleMorMode()
            self.child.sendline("") # "" is used in the fst-mor to toggle between analyse/generate
            self.child.expect(["generate> ", pexpect.EOF])
            self.child.before
        self.child.sendline(word)
        try:
            self.child.expect(["generate> ", pexpect.EOF])
        except pexpect.TIMEOUT:
            sys.stderr.write('Warning: timeout while waiting for fst-mor\n')
            sys.stderr.write('String: {0}'.format(word))
            return []
        result = self.child.before.split("\r\n")[1:-1]
        if len(result) == 1 and re.match("^no result for ", result[0]):
            result = []
        return result

    # if you just want to play around you can use this function
    def openShell(self):

        while True:
            input_string = raw_input("input<<<<")
            if input_string == "":
                self.toggleMorMode()
            self.child.sendline(input_string)
            if self.morAnalyseMode == True:
                self.child.expect(["analyze> ", pexpect.EOF])
            else:
                self.child.expect(["generate> ", pexpect.EOF])

    def toggleMorMode(self):
        self.morAnalyseMode = not self.morAnalyseMode