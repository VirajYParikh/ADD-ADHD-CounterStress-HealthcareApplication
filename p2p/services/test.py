import argparse
import os
import sys
import asyncio
import node_connection

from messaging import message
import socket
import context_transfer

# Input the context
"""Change your request context below this line
================================================"""
raw_context = ['Health', 'HeartRate', 'Stress Detection', 'ASD Research', 'Meyer']
print("Input Context (" + ','.join(raw_context)+ ")")
"""=============================================
Change your request context above this line"""

domain = raw_context[0]
dimension = raw_context[1]
application_area = raw_context[2]
business_problem = raw_context[3]
customer_profile = raw_context[4]

p1 = context_transfer.parser(domain, dimension, application_area, business_problem, customer_profile)
context_str = ','.join(p1.process())
print("context string transfers into (" + context_str+ ")")
