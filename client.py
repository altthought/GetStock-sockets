#==================================================================client.py==#
# UDP Client to request stock prices via GetStock 1.5 protocol                #
# GetStock client - Networks Final Project                                    #
#=============================================================================#
# Notes:                                                                      #
#        1) GetStock Server assumed running on IP_ADDR at PORT                #
#        2) This client requires Python 3, (Python 3.4+ preferred)            #
#-----------------------------------------------------------------------------#
# Bugs: none known                                                            #
#-----------------------------------------------------------------------------#
# Build & Execute: python3 client.py                                          #
# Build & Execute (debug mode): python3 client.py -debug                      #
#-----------------------------------------------------------------------------#
# Author:  John Culp                                                          #
#          University of South Florida                                        #
#          jculp1@mail.usf.edu                                                #
#                                                                             #
# Author:  Stephen Hull                                                       #
#          University of South Florida                                        #
#          shull@mail.usf.edu                                                 #
#                                                                             #
# References (for Python sockets programming):                                #
# "Learning Python Network Programming", Sarker and Washington, 2015, Print.  #
#-----------------------------------------------------------------------------#
# History: (11/26/2015) -- conformed to Christensen's style guidelines        #
#          (11/25/2015) -- build debug feature to build custom packet         #
#          (11/24/2015) -- fix stock price fixing to avoid printing '-1'      #
#          (11/24/2015) -- conformed to GetStock standard 1.5                 #
#          (11/16/2015) -- rebuild to conform to standard 1.4                 #
#          (11/14/2015) -- fix 5 second timeout                               #
#=============================================================================#

# Imports:                                                                    
# for sockets library and UDP packet information                              
from socket import socket, AF_INET, SOCK_DGRAM, timeout                       
from socket import error as s_error # socket error responses (bind fail, etc)                    
import sys # for command line arguments (sys.argv)                                                                 
#-----------------------------------------------------------------------------
# UDP constants                                                               
MAX_SIZE = 4096                                                               
PORT = 1050                                                                   
IP_ADDR = "127.0.0.1" # hard-coded -- must be bound to GetStock server                                                       
#-----------------------------------------------------------------------------
# GetStock client constants                                                   
COM_FIELDS = 1 # number of fields in a command response                       
ATTEMPT_LIMIT = 3 # max number of attempts to transmit a packet               
BAD_STOCK = "-1" # mark a stock value as non-existent         
#-----------------------------------------------------------------------------



#=============================================================================
# build UDP packet to send from client-->server                               
#-----------------------------------------------------------------------------
# Input: command type, username, stock names as CSV (comma sep values)        
# Output: byte-string for use in UDP datagram                                
#=============================================================================
def buildPacket(cmd,u_name,stocks_csv=None):
  # REG/UNR packet
  if cmd in ["REG","UNR"]:
    return bytes("{0},{1};".format(cmd,u_name), "utf-8")

  # quote packet
  elif cmd == "QUO" and stocks_csv is not None:
    return bytes("{0},{1},{2};".format(cmd,u_name,stocks_csv), "utf-8")

  # debug packet
  else:
    if stocks_csv:
      return bytes("{0},{1},{2};".format(cmd,u_name,stocks_csv), "utf-8")
    elif not stocks_csv:
      return bytes("{0},{1};".format(cmd,u_name), "utf-8")

# --- CLIENT starts here ---

# check if we have enabled debug mode
debug_mode = False
if len(sys.argv) > 1:
  debug_mode = (sys.argv[1] == "-debug")

try:
  # bind UDP socket, setup 5 second timeout
  c_sock = socket(AF_INET,SOCK_DGRAM)
  c_sock.settimeout(5)
except s_error as s_err:
  print("Socket error!\n",s_err)
  sys.exit(-1)

# dictionary of user-readable response codes
response_codes = {
"ROK": "Request OK",
"INC": "Invalid command",
"INP": "Invalid parameter",
"UAE": "Username already exists",
"UNR": "Username not registered",
"INU": "Invalid username"
}

# outgoing packet to be filled in by choices below
out_pkt = None

while True:
  # reset the number of attempts
  attempts = 0
  # store comma separated quotes (if quote packet formed)
  quote_csv = None

  if debug_mode:
    choice = input("(R)egister / (U)nregister / request (Q)uote / " +
     "(D)ebug packet / (E)xit: ")
  # normal mode
  else:
    choice = input("(R)egister / (U)nregister / request (Q)uote / " +
     "(E)xit: ")

  if choice in "rR" and choice != "":
    # build a REG packet 
    given_username = input("username: ")
    out_pkt = buildPacket("REG",given_username)

  elif choice in "uU" and choice != "":
    # build an UNR packet
    given_username = input("username: ")
    out_pkt = buildPacket("UNR",given_username)

  elif choice in "qQ" and choice != "":
    # build quote packet 
    given_username = input("username: ")
    quote_csv = input("Quote CSV: ")
    out_pkt = buildPacket("QUO",given_username,quote_csv)

  # custom packet (debug mode only)
  elif choice in 'dD' and debug_mode and choice != "":
    command = input("command: ")
    username = input("username: ") 
    quote_csv = input("quote_csv or blank to ignore: ")
    if not quote_csv:
      out_pkt = buildPacket(command,username)
    else:
      out_pkt = buildPacket(command,username,quote_csv)

  # reprompt if invalid input
  elif choice in 'eE' or choice == "":
    break

  # only retry if under the correct number of attempts
  while attempts < ATTEMPT_LIMIT:
    # send out chosen packet, mark our attempt
    c_sock.sendto(out_pkt, (IP_ADDR,PORT) )
    attempts = attempts + 1
    # receive CSV stock values, decode them 
    try:
      raw_data,addr = c_sock.recvfrom(MAX_SIZE)
      response = raw_data.decode("utf-8")
      # remove semicolon
      response = response.split(';')
      # split on comma (for fields)
      response_fields = response[0].split(',')
      # print user-facing message based on response
      print(response_codes[response_fields[0]])
      # if we receive more than command -- it is a stock response
      if len(response_fields) > 1:
        # build price table from quotes list and received prices
        price_table = list(zip(quote_csv.split(','), \
        response_fields[COM_FIELDS:]))
        # print stock quotes, treat "-1" as "invalid stock"
        for stock_quote in price_table:
          if stock_quote[1] == BAD_STOCK:
            print("{} : invalid stock".format(stock_quote[0]))
          else:
            print("{} : {}".format(stock_quote[0],stock_quote[1]))
      # don't retry on successful response
      break
    
    # on timeout, try again
    except timeout:
      if attempts < ATTEMPT_LIMIT:
        print("timeout -- retry...".format(attempts))
      else:
        print("timeout limit exceeded")

    except s_error as s_err:
      print("Socket error!\n",s_err)
      sys.exit(-1)

# program exit
c_sock.close()
print('socket closed')




