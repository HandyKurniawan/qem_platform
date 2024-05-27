import numpy as np
import signal 
import random

# ###########################################
# transversal CNOT error
# transversal CNOT between two blocks, where 
#     N is the length of each block
#     p is the probability of a CNOT failure
# ###########################################
list_x1_z1_x2_z2__ = np.array([[0, 0, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0], [0, 0, 1, 1], [0, 1, 0, 0], [0, 1, 0, 1], [0, 1, 1, 0], [0, 1, 1, 1], [1, 0, 0, 0], [1, 0, 0, 1], [1, 0, 1, 0], [1, 0, 1, 1], [1, 1, 0, 0], [1, 1, 0, 1], [1, 1, 1, 0], [1, 1, 1, 1]], dtype=int)

def transcnot_er(N,p):

	# erri__: error indicator vector
	# vector of length N, drawn from the Bernoulli distribution with proba p
	erri__ = np.random.binomial(1, p, N)  # 0 - no error, 1 - error
	
	# replce 1's in erri__, by random integers between 1 and 15
	erri__ = erri__ * np.floor(15*np.random.random(N) + 1).astype(int)
	
	# set the pauli error 
	# error__: N rows, with each row indicating the [x1, z1, x2, z2] error on the corresponding qubit
	error__ = list_x1_z1_x2_z2__[erri__,:]

	# returned values [list1x, list1z, list2x, list2z] = error__.transpose()
	# where: list1x = array or length N, indicating X-errors on the first block
	# where: list1z = array or length N, indicating Z-errors on the first block
	# where: list2x = array or length N, indicating X-errors on the second block
	# where: list2z = array or length N, indicating Z-errors on the second block
	return error__.transpose()

# ################################################################
# information position for Q1 and Shor codes -- counting from ZERO
# Table I (Best information positions for low error probabilities) 
# depolarizing noise model, ignoring correlation
# ################################################################ 
def infpos(n, type="q1"):
	 
	# ipos value, counting from zero: 0 <= ipos < 2**n
	if type == "q1":
		if n == 3:
			ipos = 3
		elif n == 4:
			ipos = 6
		elif n == 5:
			ipos = 7
		elif n == 6:
			ipos = 22
		elif n == 7:
			ipos = 15
		elif n == 8:
			ipos = 90
		elif n == 9:
			ipos = 31
		elif n == 10:
			ipos = 362
		elif n == 11:
			ipos = 95
		elif n == 12:
			ipos = 1450
		else:
			raise TypeError("Illegal 'n' value")
			
	elif type == "shor" or type == "sh":
		if n == 3:
			ipos = 3
		elif n == 4:
			ipos = 3
		elif n == 5:
			ipos = 7
		elif n == 6:
			ipos = 7
		elif n == 7:
			ipos = 15
		elif n == 8:
			ipos = 15
		elif n == 9:
			ipos = 31
		elif n == 10:
			ipos = 31
		elif n == 11:
			ipos = 63
		elif n == 12:
			ipos = 63
		else:
			raise TypeError("Illegal 'n' value")
	
	else:
		raise TypeError("Illegal 'type' value")
	
	return ipos

# ############################################
# signal handler for Ctrl-C keyboard interrupt
# ############################################
def ctrlC_handler(signum, frame):
	print("\n\nKeyboardInterrupt")
	exit(1)
