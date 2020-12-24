#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu 24 Dec 2020

@author: ravbag
"""

# A file describing how to implement the Sieve of Eratosthenes in Python

def prime_eratosthenes(n):
    prime_list =[]
    for i in range (2, n+1):
        if i not in prime_list:
            print (i)
            for j in range(i*i, n+1, i):
                prime_list.append(j)

prime_eratosthenes(10000)
