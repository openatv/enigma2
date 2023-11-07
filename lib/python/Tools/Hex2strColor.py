#!/usr/bin/python
# -*- coding: utf-8 -*-
# Converts hex colors to formatted strings,
# suitable for embedding in python code.


def Hex2strColor(rgb):
	return r"\c%08x" % rgb
