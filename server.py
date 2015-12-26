#==================================================================server.py==#
# Blocking UDP Server to provide stock prices via GetStock 1.5 protocol       #
# GetStock server - Networks Final Project                                    #
#=============================================================================#
# Notes:                                                                      #
#        1) this is a blocking UDP server                                     #
#        2) Stocks values are read from a STOCK_FILE (defined below) and      #
#           stored in a dictionary on server startup. File must exist.        #
#        3) This server requires Python 3, (Python 3.4+ preferred)            #
#-----------------------------------------------------------------------------#
# Example "stockfile.txt": with stock name and price space by whitespace      #
# IBM 121.11                                                                  #
# FB 23.22                                                                    #
# NFLX 11.99                                                                  #
# CSCO 43.33                                                                  #
#-----------------------------------------------------------------------------#
# Example run: (no output to stdout unless stockfile is missing)              #
#-----------------------------------------------------------------------------#
# Bugs: none known                                                            #
#-----------------------------------------------------------------------------#
# Build & Execute: python3 server.py                                          #
#-----------------------------------------------------------------------------#
# Author:  John Culp                                                          #
#          University of South Florida                                        #
#          jculp1@mail.usf.edu                                                #
#                                                                             #
# Author:  Stephen Hull                                                       #
#          University of South Florida                                        #
#          shull@mail.usf.edu                                                 #
#-----------------------------------------------------------------------------#
# References (for Python sockets programming):                                #
# "Learning Python Network Programming", Sarker and Washington, 2015, Print.  #
#-----------------------------------------------------------------------------#
# History: (11/26/2015) -- conformed to Christensen's style guidelines        #
#          (11/24/2015) -- conformed to GetStock standard 1.5                 #
#          (11/16/2015) -- rebuild to conform to standard 1.4                 #
#          (11/14/2015) -- use dictionary structure for stock prices          #
#=============================================================================#
#--imported modules----------------------------------
from socket import socket, AF_INET, SOCK_DGRAM
from socket import error as s_error # catch bind failures
import re # to parse stock value from stockfile.txt
from sys import exit # to exit if stockfile.txt not found

#--Global Constants--UDP-----------------------------
MAX_SIZE = 4096 # buffer size for UDP
PORT = 1050 # port number for GetStock server

#--Global Constants--GetStock server--------------------------------
MAX_NAME = 32 # upper limit on length of username 
QUOTE_FIELDS = 3 # number of fields in a valid received QUO packet
REG_FIELDS = 2 # number of fields in a valid received REG/UNR packet
BAD_STOCK = "-1" # inserted into response if stock does not exist
STOCK_FILE = "stockfile.txt" # filename of stock file in current dir


#=============================================================#
# build UDP packet to send from server-->client               #
#-------------------------------------------------------------#
# Input: command type, stock names as CSV (comma sep values)  #
# Output: byte-string for use in UDP datagram                 #
#=============================================================#
def buildPacket(command,stock_csv=None):
  # build a QUO packet by pulling from dictionary or bad_stock
  if command == "QUO" and stock_csv is not None:
    price_list = []
    for name in stock_csv.split(","):
      if name in stock_dict:
        price_list.append(stock_dict[name])
      else:
        price_list.append(BAD_STOCK)
    # form CSV price list for packet
    price_csv = ",".join(price_list)
    return bytes("{},{};".format("ROK",price_csv),"utf-8")
  # UNR/REG just return a response
  else:
    return bytes("{};".format(command),"utf-8")

#=============================================================#
# load stock prices from txt file into dictionary             #
#-------------------------------------------------------------#
# Input: txt filename to load stock names/prices              #
# Output: dictionary containing keys=stock_names, val=prices  #
#=============================================================#
def loadStockDict(stockfile_name):
  try:
    stock_dict = {}
    with open(stockfile_name) as f:
      for line in f:
        # stocks in form ABCD ###.##
        valid_stock = re.match(r"([A-Z]+) (\d+\.\d\d)",line)
        if valid_stock:
          # stock_dict[found name] = found price
            stock_dict[valid_stock.group(1)] = valid_stock.group(2)
    return stock_dict
  # failure to load stockfile forces exit
  except (FileNotFoundError,PermissionError) as err:
    print("stock file read error (check file exists)")
    return None

# build stock dictionary from txt file, or quit
stock_dict = loadStockDict(STOCK_FILE)
if not stock_dict:
  exit(-1)

# at first, there are no registered users
reg_users = []

try:
  # bind blocking socket as UDP datagram on PORT
  s_sock = socket(AF_INET,SOCK_DGRAM)
  s_sock.bind( ("", PORT) )
except s_error as s_err:
  print("Socket error!\n",s_err)
  exit(-1)

try:
  # always serve requests
  while True:
    #get request from new connection
    # grab raw byte string from client-side
    try:
      raw_data,addr = s_sock.recvfrom(MAX_SIZE) 
      data = raw_data.decode("utf-8") 
    except s_error as s_err:
      print("recvfrom() failed\n",s_err)
      sys.exit(-1)

    # create list from comma separated quotes
    recv_pkt_flds = data.split(",") 
    send_pkt = None

    # first check for invalid command, valid format
    if recv_pkt_flds[0] not in ["REG", "UNR", "QUO"]:
      send_pkt = buildPacket("INC")

      # attempted REG packet
    elif len(recv_pkt_flds) == REG_FIELDS and recv_pkt_flds[0] in ["REG","UNR"] \
     and recv_pkt_flds[1].endswith(';'):
      # check if ; ends username field and length is correct
      given_command = recv_pkt_flds[0]
      strip_semicolon = recv_pkt_flds[1][0:-1] # strip ';'
      given_uname = strip_semicolon.lower() # make lowercase

      # ensure name is correct size / alphanumeric only, or build INU packet
      if len(given_uname) > MAX_SIZE or not given_uname.isalnum():
        send_pkt = buildPacket("INU")

      # this is a valid REG/UNR packet
      else:
        # register packet and username free, add to list, request ok
        if given_command == "REG" and given_uname not in reg_users:
          reg_users.append(given_uname)
          send_pkt = buildPacket("ROK")
        # can't register existing usernames
        elif given_command == "REG" and given_uname in reg_users:
          send_pkt = buildPacket("UAE")
        # can't unregister users that don't exist
        elif given_command == "UNR" and given_uname not in reg_users:
          send_pkt = buildPacket("UNR")
        # remove existing user, request ok
        elif given_command == "UNR" and given_uname in reg_users:
          reg_users.remove(given_uname)
          send_pkt = buildPacket("ROK")

    # attempted QUO packet
    elif len(recv_pkt_flds) >= QUOTE_FIELDS and recv_pkt_flds[0] == "QUO" \
     and data.endswith(';'):
      given_uname = recv_pkt_flds[1].lower()
      # ensure name is correct size, alphanumeric, or build INU packet
      if len(given_uname) > MAX_NAME or not given_uname.isalnum():
        send_pkt = buildPacket("INU")
      # unregistered users cannot fetch quotes!
      elif given_uname not in reg_users:
        send_pkt = buildPacket("UNR")
      # valid QUO packet
      else:
        # join remaining fields into one csv
        w_semicolon = ",".join(recv_pkt_flds[2:])
        quotes_csv = w_semicolon[:-1] # strip semicolon
        # CSV in form: ABCD,BCDE,EFGH,...,WXYZ, build and send
        if re.match(r"^([A-Z]{2,5},)*[A-Z]{2,5}$", quotes_csv):
          send_pkt = buildPacket("QUO",quotes_csv)
        else:
          send_pkt = buildPacket("INP")


    # packet does not conform to any known pattern -- invalid parameters
    else:
      send_pkt = buildPacket("INP")

    # send response to client
    try:
      if send_pkt is None:
        print("packet not formed")
        sys.exit(-1)

      s_sock.sendto(send_pkt,addr)
    except s_error as s_err:
      print("Failed to send response!\n",s_err)

# Control-C (or equivalent) closes socket/kills server
except KeyboardInterrupt:
  s_sock.close()
  print("socket closed")
  exit(0)

