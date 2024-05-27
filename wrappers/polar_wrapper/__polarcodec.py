import numpy as np
import signal 

# ############################################################################
# polar encoder: encoding is done in-place, meaning that the input data vector 
# U (uncoded bits) is modified by the function.  after encoding, U corresponds
# to the encoded bits (codeword)
# ############################################################################
# input argument
# U: numpy.array, vector on uncoded bits
#  : modified by the function (changed to vector of encoded bits)
# returned value
# U: vector of encoded bits
def polarenc(U):
	N = len(U)
	h = N//2
            
	if N == 1:
		return U
	else:
   
        # divide U into two halves of equal length
		U1 = U[0:h]
		U2 = U[h:N]
        
		# call polar encoder for U1 and U2
		polarenc(U1)
		polarenc(U2)
        
        # do the BITWISE CNOT gate on two lists with U2 as control
		U[0:h] = (U1 + U2) % 2
		
		return U

# #########################################################
# reverse polar encoder:  polar encoder with reversed cnots 
# equivalent to: reverse U, polar encode U, reverse U again
# #########################################################
def revpolarenc(U):
	N = len(U)
	h = N//2
            
	if N == 1:
		return U
	else:
		
        # divide U into two halves of equal length
		U1 = U[0:h]
		U2 = U[h:N]
		
		# call the revserse polar encoder for U1 and U2
		revpolarenc(U1)
		revpolarenc(U2)
		
        # do the BITWISE CNOT gate on two lists with U1 as control
		U[h:N] = (U1 + U2) % 2
		
		return U


# #####################################################################################
# polar decoder: this implementation supports only one information bit per coded block
# as we only decode one decoding tree (correspopnding to the information position ipos),
# llrs update is performed in place.  thus, after decoding, the llr_list contains only
# one llr value, corresponding to u_ipos (uncoded bit at position ipos)
# #####################################################################################
# input argument
# llr_list: numpy.array, vector of llr values
#         : modified by the function (changed to scalar llr value, corresponding to u_ipos)
#     ipos: scalar, information position
# returned value
#   u_ipos: guessed value of the uncoded bit (u) at position ipos
def polardec(llr_list, ipos):
	N  = len(llr_list)   # code length
	ip = ipos  # copy of ipos (information position)
	
	while N > 1:
		h = N//2
		
		llr_list1 = llr_list[0:h]
		llr_list2 = llr_list[h:N]
		
		if ip < h: # decoding bad channel
			llr_list = np.sign(llr_list1)*np.sign(llr_list2)*np.minimum(abs(llr_list1), abs(llr_list2))
		
		else: # ip >= h: decoding good channel
			llr_list = llr_list1 + llr_list2
			ip = ip - h
		
		# update N
		N = h
	
	llr_ipos = llr_list[0]
	if llr_ipos > 0:
		u_ipos = 0
	elif llr_ipos < 0:
		u_ipos = 1
	else:
		u_ipos = np.random.randint(2)
	
	return u_ipos


# ########################################################
# reverse polar decoder: polar decoder with reversed cnots 
# ########################################################
def revpolardec(llr_list, ipos):
	N  = len(llr_list)   # code length
	ip = ipos  # copy of ipos (information position)
	
	while N > 1:
		h = N//2
		
		llr_list1 = llr_list[0:h]
		llr_list2 = llr_list[h:N]
		
		if ip < h: # decoding good channel
			llr_list = llr_list1 + llr_list2
		
		else: # ip >= h: decoding bad channel
			llr_list = np.sign(llr_list1)*np.sign(llr_list2)*np.minimum(abs(llr_list1), abs(llr_list2))
			ip = ip - h
		
		# update N
		N = h
	
	llr_ipos = llr_list[0]
	if llr_ipos > 0:
		u_ipos = 0
	elif llr_ipos < 0:
		u_ipos = 1
	else:
		u_ipos = np.random.randint(2)
	
	return u_ipos


#### ################################################################### ####
####              POLAR DECODER DENSITY EVOLUTION                        ####
#### ################################################################### ####
# this implementation of DE supports only one information bit per coded block

# ##############################################
# density evolution for decoding the bad channel 
# ##############################################
def bad_channel_pdf(ptXpdf_in, z_idx, x_num):
	
	# returned value
	ptXpdf_out = np.zeros(x_num)
 
    # xor_out = sgn(xor_in1)*sgn(xor_in2)*min(|xor_in1|, |xor_in2|)
    # xor_in1 and xor_in2 are both distributed according to ptXpdf_in
    
    #   x_idx:    0,       1,    ...  , z_idx, z_idx+1, .....,  x_num-1
    #    x_pt: -z_idx, -z_idx+1, ... ,    0,     1,  ...  , -z_idx+x_num-1
 
    # ptXpdf_out[x_idx] = Pr( xor_out = -z_idx+x_idx) = Pr( xor_out = -z_idx+x_idx)
    # = Pr( sgn(xor_in1)*sgn(xor_in2)*min(|xor_in1|, |xor_in2|) = -z_idx+x_idx )
    
    # if -z_idx+x_idx < 0 <=> x_idx < z_idx
    #    ptXpdf_out[x_idx] = F(idx) - F(idx-1),
    #    where
    #    F(idx) = Pr( sgn(xor_in1)*sgn(xor_in2)*min(|xor_in1|, |xor_in2|) <= -z_idx+x_idx )
    #           =   Pr(xor_in1 <= -z_idx+x_idx)*Pr(xor_in2 >=  z_idx-x_idx)
    #             + Pr(xor_in1 >=  z_idx-x_idx)*Pr(xor_in2 <= -z_idx+x_idx)
    #     = 2*ptXpdf_in[0 to x_idx]*ptXpdf_in[2*z_idx-x_idx to end]
    
    # compute F(x_idx) and store its value in ptXpdf_out[x_idx]
	sum_pdf1 = 0
	sum_pdf2 = 0
	
	for xp_idx in range (2*z_idx+1, x_num):
		sum_pdf2 += ptXpdf_in[xp_idx]
	
	for x_idx in range (0, z_idx):
		sum_pdf1 += ptXpdf_in[x_idx]
		sum_pdf2 += ptXpdf_in[2*z_idx-x_idx]
		ptXpdf_out[x_idx] = 2*sum_pdf1*sum_pdf2
		
    # copmpute ptXpdf_out[x_idx] = F(x_idx) - F(x_idx-1)
	for x_idx in range(z_idx-1, 0, -1):  
		ptXpdf_out[x_idx] -= ptXpdf_out[x_idx-1]
	
    
    # if -z_idx+x_idx = 0 <=> x_idx = z_idx
    #    ptXpdf_out[x_idx] = Pr(xor_in1 = 0) + Pr(xor_in2 = 0) - Pr(xor_in1 = 0) + Pr(xor_in2 = 0)
    #    = 2*ptXpdf_in[x_idx] - ptXpdf_in[x_idx]*ptXpdf_in[x_idx]
	ptXpdf_out[z_idx] = 2*ptXpdf_in[z_idx] - ptXpdf_in[z_idx]*ptXpdf_in[z_idx]
    
    # if -z_idx+x_idx > 0 <=> x_idx > z_idx
    #    ptXpdf_out[x_idx] = F(idx) - F(idx+1),
    #    where
    #    F(idx) = Pr( sgn(xor_in1)*sgn(xor_in2)*min(|xor_in1|, |xor_in2|) >= -z_idx+x_idx )
    #           =   Pr(xor_in1 >= -z_idx+x_idx)*Pr(xor_in2 >= -z_idx+x_idx)
    #             + Pr(xor_in1 <=  z_idx-x_idx)*Pr(xor_in2 <=  z_idx-x_idx)
    #     = ptXpdf_in[x_idx to end]*ptXpdf_in[x_idx to end] + ptXpdf_in[0 to 2*z_idx-x_idx]*ptXpdf_in[0 to 2*z_idx-x_idx]
    
    # compute F(x_idx) and store its value in ptXpdf_out[x_idx]
	sum_pdf1 = 0
	sum_pdf2 = 0
	
	for x_idx in range(x_num-1, 2*z_idx, -1): 
		sum_pdf1 += ptXpdf_in[x_idx]
		
	for x_idx in range(2*z_idx, z_idx, -1):
		sum_pdf1 += ptXpdf_in[x_idx]
		sum_pdf2 += ptXpdf_in[2*z_idx-x_idx]
		ptXpdf_out[x_idx] = sum_pdf1*sum_pdf1 + sum_pdf2*sum_pdf2
	
    
    # compute ptXpdf_out[x_idx] = F(x_idx) - F(x_idx+1)
	for x_idx in range(z_idx+1, x_num-1):
		ptXpdf_out[x_idx] -= ptXpdf_out[x_idx+1]
	
    
    # normalize: sum_pdf must be equal to 1
	sum_pdf = 0
	for x_idx in range(0, x_num):
		sum_pdf += ptXpdf_out[x_idx]
	
	for x_idx in range(0, x_num):
		ptXpdf_out[x_idx] /= sum_pdf
	
	return ptXpdf_out



# ###############################################
# density evolution for decoding the good channel 
# ###############################################
def good_channel_pdf(ptXpdf_in, z_idx, x_num):

    # returned value
	ptXpdf_out = np.zeros(x_num)
	
	# pdf buffer of size s_num = 2*x_num-1
	s_num = 2*x_num-1
	pdf_buf = np.zeros(s_num)
    
    
    # rep_out = rep_in1 + rep_in2
    # rep_in1 and rep_in2 are both distributed according to ptXpdf_in
    
    #   x_idx:    0,       1,    ...  , z_idx, z_idx+1, .....,  x_num-1
    #    x_pt: -z_idx, -z_idx+1, ... ,    0,     1,  ...  , -z_idx+x_num-1
    
    # s = x1 + x2
    # s_left = 2*x_left => sz_idx = -s_left = -2*x_left = 2*z_idx;
    # s_num  = 2*x_num-1;
    # s_idx  = 0, 1, ...,s_num-1
    # pdf_buf[s_idx] = Pr(rep_out = -sz_idx+s_idx) 
    #                = Pr(rep_in1 + rep_in2 = -2*z_idx+s_idx)
    
	for x1_idx in range(0, x_num):
		for x2_idx in range(0, x_num):
			s_idx = x1_idx + x2_idx;
			pdf_buf[s_idx] += ptXpdf_in[x1_idx]*ptXpdf_in[x2_idx]
    
	sum_pdf = 0
	for x_idx in range(1, x_num-1):
		s_idx = 2*x_idx;
		ptXpdf_out[x_idx] = pdf_buf[s_idx-1]/2.0 + pdf_buf[s_idx] + pdf_buf[s_idx+1]/2.0
		sum_pdf += ptXpdf_out[x_idx]
		
	ptXpdf_out[0] = pdf_buf[0] + pdf_buf[1]/2.0
	ptXpdf_out[x_num-1] = pdf_buf[s_num-2]/2.0 + pdf_buf[s_num-1]
	sum_pdf += (ptXpdf_out[0] + ptXpdf_out[x_num-1])
  
    # normalize: sum_pdf must be equal to 1
	for x_idx in range(0, x_num):
		ptXpdf_out[x_idx] /= sum_pdf
    
	return ptXpdf_out


# ########################################################################
# polar decoder: density evolution for one information bit per coded block
# ########################################################################
# input argument
#  pin: scalar, input bit error probability
#    n: number of polarization levels (code length N = 2**n)
# ipos: scalar, information position
# returned value
# pout: scalar, output error probability for the information bit at position ipos
def polardec_de__(pin, n, ipos):
	N  = 2**n  # code length
	ip = ipos  # copy of ipos (information position)
	
	# M = number of quantization levels (positive values) for the pdf
	if n < 10:
		M = 2**(n+1)  
	else:
		M = 2**10 

	z_idx = M    # zero index -- python numbering (starting from 0)
	l_idx = M-2  # llr indx = z_indx + l_indx
	
	# set the "normalized" pdf_in -- llr value is normalized to lX=1
	x_num  = 2*M+1
	ptXpdf = np.zeros(x_num)
	ptXpdf[z_idx+l_idx] = 1.0-pin;  # probability llr = +lX
	ptXpdf[z_idx-l_idx] =  pin;     # probability llr = -lX
	
	while N > 1:
		h = N//2
		
		if ip < h: # decoding bad channel
			ptXpdf = bad_channel_pdf(ptXpdf, z_idx, x_num)
		
		else: # ip >= h: decoding good channel
			ptXpdf = good_channel_pdf(ptXpdf, z_idx, x_num)
			ip = ip - h
		
		# update N
		N = h
	
	# compute output error probability
	pout = 0.0
	for x_idx in range (0, z_idx):
		pout += ptXpdf[x_idx]
		
	pout += (ptXpdf[z_idx]/2.0)
	
	return pout

# ################################################################################
# reverse polar decoder: density evolution for one information bit per coded block
# ################################################################################
# input argument
#  pin: scalar, input bit error probability
#    n: number of polarization levels (code length N = 2**n)
# ipos: scalar, information position
# returned value
# pout: scalar, output error probability for the information bit at position ipos
def revpolardec_de__(pin, n, ipos):
	N  = 2**n  # code length
	ip = ipos  # copy of ipos (information position)
	
	# M = number of quantization levels (positive values) for the pdf
	if n < 10:
		M = 2**(n+1)  
	else:
		M = 2**10 

	z_idx = M    # zero index -- python numbering (starting from 0)
	l_idx = M-2  # llr indx = z_indx + l_indx
	
	# set the "normalized" pdf_in -- llr value is normalized to lX=1
	x_num  = 2*M+1
	ptXpdf = np.zeros(x_num)
	ptXpdf[z_idx+l_idx] = 1.0-pin;  # probability llr = +lX
	ptXpdf[z_idx-l_idx] =  pin;     # probability llr = -lX
	
	while N > 1:
		h = N//2
		
		if ip < h: # decoding good channel
			ptXpdf = good_channel_pdf(ptXpdf, z_idx, x_num)
		
		else: # ip >= h: decoding bad channel
			ptXpdf = bad_channel_pdf(ptXpdf, z_idx, x_num)
			ip = ip - h
		
		# update N
		N = h
	
	# compute output error probability
	pout = 0.0
	for x_idx in range (0, z_idx):
		pout += ptXpdf[x_idx]
		
	pout += (ptXpdf[z_idx]/2.0)
	
	return pout

# ################################################################
# reduce error weight
# a greedy algorithm to find an equivalent error of reduced weight
# ################################################################
def reduce_Xerr(Xerr, ipos):
	N = len(Xerr) # code length
	count = 0
	
	while 1:
		for ip in range(ipos+1, N):
			# X-generator corresponding to an X in position ip
			Xgen = np.zeros(N)  # all-zero
			Xgen[ip] = 1        # set ip position to 1
			polarenc(Xgen)      # encode
			
			Xerr__ = (Xerr + Xgen) % 2
			if np.sum(Xerr__) < np.sum(Xerr):
				Xerr[:] = Xerr__[:]
				count = 0
			else:
				count += 1
				
			if count == N-1-ipos:
				break
			
		if count == N-1-ipos:
			break
		
	return Xerr	


def reduce_Zerr(Zerr, ipos):
	N = len(Zerr) # code length
	count = 0
	
	while 1:
		for ip in range(0, ipos):
			# Z-generator corresponding to an Z in position ip
			Zgen = np.zeros(N)  # all-zero
			Zgen[ip] = 1        # set ip position to 1
			revpolarenc(Zgen)   # encode
			
			Zerr__ = (Zerr + Zgen) % 2
			if np.sum(Zerr__) < np.sum(Zerr):
				Zerr[:] = Zerr__[:]
				count = 0
			else:
				count += 1
				
			if count == ipos:
				break
			
		if count == ipos:
			break
		
	return Zerr	

