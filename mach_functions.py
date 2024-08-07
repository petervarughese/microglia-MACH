import cv2
import matplotlib.pyplot as plt
import numpy as np
import sys
from skimage import transform
import imutils
import utils
from scipy import ndimage
from scipy.ndimage import measurements
from scipy.ndimage import morphology
import yaml
import os

sys.path = ["./matchedmyo/"] + sys.path
import util
from sklearn.decomposition import PCA


truthColors = {
    'ram': 'green',
    'rod': 'red',
    'amoe': 'cyan',
    'hyp': 'blue',
    'dys': 'yellow'
    }

colorchannels = {
    'green' : [1],
    'red' : [0],
    'blue': [2],
    'yellow': [0,1],
    'cyan': [1,2],
    }


# a dic to store the PC1/PC2 coordinates of classified image
coords = {'ram':[],
         'rod':[],
         'dys':[],
          'hyp':[]}
# a dic to store classified image
pcaClassifiedImages = {'ram':[],
                       'rod':[],
                       'dys':[],
                       'hyp':[],
                       'amoe':[]}


def invert_gray_scale(images):
    """
    make cells as white and background as black
    """
    new_images=[]
    for i in images:
        new_images.append(255 - i)
    return new_images


def normalize(image):
    """
    Normolize the gray_scale image
    """
    newimage = image/np.max(image)
    return newimage

def displayMultImage(images,nColumns=10,cmap=None,numbering=True):
    """
    Function to display the cropped representative microglia cells
    """
    N = len(images)
    if cmap == None:
        # check the if the image is RGB or grayscale
        if len(np.shape(images[0])) == 2:
                cmap='gray'
        else:
                cmap=None

            
        #now of rows, each row has maxi 25 columns
    #nColumns = 25
    nRows = np.ceil(N / nColumns)
    #nColumns = 25
        
    figure = plt.figure(figsize=(nColumns,nRows))
            
    for i,img in enumerate(images):
            plt.subplot(nRows,nColumns,i+1)
            plt.imshow(img,cmap=cmap,aspect="auto")
            plt.xticks([])
            plt.yticks([])
            if numbering:
                plt.title(str(i+1))
            plt.subplots_adjust(wspace=0.01,hspace=0.01)

def invertGrayImage(oriImage):
    """
    Converts the image to gray scale, then inverse the white/black and finally 
    normolize it

    The oriImage is the output of cv2.imread, by default, the color channels are 
    BGR, so we use cv2.COLOR_BGR2GRAY to convert it to gray scale
    """
    
    newimage = normalize(invert_gray_scale(cv2.cvtColor(oriImage,cv2.COLOR_BGR2GRAY)))

    return newimage


def alignRodCellvertically(Image,
                            ifbinary=False,
                            thres = 0.4, #thres value for binary image
                            plotting=False, # plotting the detected rod-direction
                            inverse=False
                            ):
    """
    automatically align rod-shaped cells vertically
    """
    #image = util.ReadImg(Imagename).astype(np.uint8)
    #grey = cv2.cvtColor(rod,cv2.COLOR_RGB2GRAY)
    if ifbinary:
        binaryimage = Image
    else:
        if inverse:
            dummy, binaryimage = cv2.threshold(cv2.cvtColor(Image,cv2.COLOR_BGR2GRAY), 255*thres, 255, cv2.THRESH_BINARY_INV)
        else:
            dummy, binaryimage = cv2.threshold(cv2.cvtColor(Image,cv2.COLOR_BGR2GRAY), 255*thres, 255, cv2.THRESH_BINARY)

    # detect the direction of rod using the hough line detection 
    # note, the angle unit is radian (1 radian = 57.2958 degree)
    Hspace, Angle, Dist = transform.hough_line(binaryimage)

    # find the peaks in the hough space
    peaks = transform.hough_line_peaks(Hspace,Angle,Dist)
    if len(peaks[0]) > 1:
        print ('More than 1 directions exist, using the first direction')


    angle = peaks[1][0]
    dist = peaks[2][0]

    #  now rotate the image based one the angle
    radianTodegree = 57.29

    rotatedImage = imutils.rotate(Image,angle*radianTodegree)
    if plotting:    
        origin = np.array((0, binaryimage.shape[1]))
        line = (dist - origin * np.cos(angle)) / np.sin(angle)
        plt.subplot(1,2,1)
        plt.imshow(Image)
        plt.plot(origin,line,'r-')

        plt.ylim([0,binaryimage.shape[1]])
        plt.xticks([])
        plt.yticks([])
        plt.title('detected directions')

        plt.subplot(1,2,2)
        plt.imshow(rotatedImage)
        plt.xticks([])
        plt.yticks([])
        plt.title('align vertically')


    return rotatedImage

def collectSelecteArea(yamlFile,BG=[202,202,196]):
    """
    collect the selected area based on info from the
    yamlFile, combine them into on image if multiple areas
    are selected. Clean the image
    """
    with open (yamlFile,'rb') as f:
        imageInfo = yaml.safe_load(f)

    imagefile =  imageInfo['ImagePath'] + "/" + imageInfo["ImageName"]
    if not os.path.isfile(imagefile):
        raise RuntimeError(f"The image {imageInfo['ImageName']} is not found")
    
    img = cv2.imread(imagefile) #cv2 read image in bgr order
    
    # combine the multiple areas into one image
    Nimages = len(imageInfo['coords'])
    if Nimages > 1:
        nRows = np.ceil(Nimages/2).astype(np.int)
        nCols = 2
        L =  imageInfo["coords"][0][2]*10
        W =  imageInfo["coords"][0][3]*10
        dimX = W*nRows
        dimY = nCols*L
        TotalImage = np.zeros((dimX,dimY,3),dtype=np.uint8)
        
        # first assign a use-defined background
        TotalImage[:,:,0] = BG[0]
        TotalImage[:,:,1] = BG[1]
        TotalImage[:,:,2] = BG[2]
        for  i in range(Nimages):
            startx = int(W*np.floor(i/2))
            endx = startx + W
            starty = int(L*(i%2))
            endy = starty + L
            x = imageInfo["coords"][i][0]*10
            y = imageInfo["coords"][i][1]*10
            L = imageInfo["coords"][i][2]*10
            W = imageInfo["coords"][i][3]*10
            TotalImage[startx:endx,starty:endy] = img[y:y+W,x:x+L]
       
    else:
        x = imageInfo["coords"][0][0]*10
        y = imageInfo["coords"][0][1]*10
        L = imageInfo["coords"][0][2]*10
        W = imageInfo["coords"][0][3]*10
        TotalImage = img[y:y+W,x:x+L]

    outputImage = dict()
    outputImage['selectedArea'] = TotalImage
    outputImage['cleanedImage'] = cleanImage(TotalImage,imageInfo["cellThres"])
    outputImage['rgbImage'] = cv2.cvtColor(TotalImage,cv2.COLOR_BGR2RGB)
    outputImage['grayImage'] = invertGrayImage(outputImage['cleanedImage'])

    return outputImage



def azimuthally_psd(image,bins=30):
    '''
    generate the PSD along radial direction, the image is grayscale
    '''
    fftimage = np.fft.fft2(image)
    
    dimes = fftimage.shape
    centerX = int(dimes[0]/2)
    centerY = int(dimes[1]/2)
    maskimage = np.ones(dimes)
    maskimage[centerX,centerY] = 0
    
    edt_mask = ndimage.distance_transform_edt(maskimage)
    
    ori_psd = np.log(np.abs(np.fft.fftshift(fftimage))**2)
    # max radial length
    mlen = np.sqrt(centerX**2+centerY**2)
    spacing = mlen/bins
    
    
    psd = []
    dist = []
    for i in np.arange(bins):
        low_limit = i*spacing
        high_limit = (i+1)*spacing
        dist_i = 0.5*(low_limit + high_limit)
        
        indx = np.logical_and(np.greater_equal(edt_mask,low_limit),np.less(edt_mask,high_limit))
        psd_i = np.sum(ori_psd[indx])/np.sum(maskimage[indx])
        psd.append(psd_i)
        dist.append(dist_i)
        
    return dist,psd


    

def rotate_image(mat, angle):
    """
    Rotates an image (angle in degrees) and expands image to avoid cropping
    """

    height, width = mat.shape[:2] # image shape has 3 dimensions
    image_center = (width/2, height/2) # getRotationMatrix2D needs coordinates in reverse order (width, height) compared to shape

    rotation_mat = cv2.getRotationMatrix2D(image_center, angle, 1.)

    # rotation calculates the cos and sin, taking absolutes of those.
    abs_cos = abs(rotation_mat[0,0]) 
    abs_sin = abs(rotation_mat[0,1])

    # find the new width and height bounds
    bound_w = int(height * abs_sin + width * abs_cos)
    bound_h = int(height * abs_cos + width * abs_sin)

    # subtract old image center (bringing image back to origo) and adding the new image center coordinates
    rotation_mat[0, 2] += bound_w/2 - image_center[0]
    rotation_mat[1, 2] += bound_h/2 - image_center[1]

    # rotate image with the new bounds and translated rotation matrix
    rotated_mat = cv2.warpAffine(mat, rotation_mat, (bound_w, bound_h))
    return rotated_mat



def divde_big_image(bigimage,grayscale=True):
    """
    divided the big grayscale image into 
    100 small images
    """
    dx = int(bigimage.shape[0]/10)
    dy = int(bigimage.shape[1]/10)
    
    if grayscale:
        small_images = [bigimage[dx*i:dx*(i+1),dy*j:dy*(j+1)]\
                for i in np.arange(10) for j in np.arange(10)]
    else:
        small_images = [bigimage[dx*i:dx*(i+1),dy*j:dy*(j+1),:]\
                for i in np.arange(10) for j in np.arange(10)]
    return small_images


def getTPFP(detectedCells,
                marked_truth,
                verbose=True,
                returnOverlap=False):
    '''
    Calculted the True Positive (TP) score and False Positive (FP) score
    given the detected cells by MACH protocol and the annotated truth image
    Both the detected cells and marked_truth are binary images.
    '''
    labels, numofgroups = measurements.label(marked_truth)

    overlap = detectedCells*marked_truth

    results = np.zeros(marked_truth.shape)
    for i in np.arange(1,numofgroups+1):
        if np.sum(overlap[labels == i]) > 1:
            results[labels==i] = 1.0

    
    labels3, numofgroups3 = measurements.label(detectedCells)
    overlap3 = detectedCells*results 
    results3 = detectedCells.copy()

    for i in np.arange(1,numofgroups3+1):
        if np.sum(overlap3[labels3 == i]) > 1:
            results3[labels3==i] = 0.0
        
    dummy1, numberoffp = measurements.label(results3)



    dummy2, numofgroups2 = measurements.label(results)
    TP = numofgroups2/numofgroups
    FP = numberoffp/numofgroups
    if verbose == True:
        print ("Found %d cells in the annoated image" % (numofgroups))
        print ("Successfully detected %d cells" % (numofgroups2))
        print ("False positively detected %d cells" % (numberoffp) )
        print ("The TP/FP rate are %5.2f and %5.3f" % (numofgroups2/numofgroups, numberoffp/numofgroups))
    
    # store the cell numbers 
    cellNums = dict()
    cellNums['AnnotatedCell'] = numofgroups
    cellNums['TPCells'] = numofgroups2
    cellNums['FPCells'] = numberoffp
        

    if returnOverlap:
        return results, results3, TP,FP, cellNums
    else:
        return TP, FP, cellNums
    

def pasteImage(image, thresd_image, color):
    '''
    Set the R/G channel value to 255 to hightlight the
    hits from bad/good filter
    '''
    newimage = image.copy()
    if color == 'green':
        newimage[thresd_image==1,1] = 255
    elif color == 'red':
        newimage[thresd_image==1,0] = 255
    elif color == 'yellow':
        newimage[thresd_image==1,0:2] = 255
    elif color == "blue":
        newimage[thresd_image==1,2] = 255
    elif color == "cyan":
        newimage[thresd_image==1,1:3] = 255
    return newimage

def cleanImage(image,cellThres=125,BG=[202,202,196]):
    """
    Cleaning the image by removing the nucleus (blue dots) and setting the background
    to a use-defined value.
    First thresholding the image using blue channel info with user-specified values (cellThres)
    as the cells and nucleus have largest contrast in this channel. 
    Then setting the background colors
    """
    blueChannel = 255 - image[:,:,0] # reverse the intentsity, the cv2 read image in BGR order, 
    # thresholding 
    thres = np.greater(blueChannel,cellThres).astype(np.float)

    newImage = image.copy()
    newImage[thres == 0, 0] = BG[0]
    newImage[thres == 0, 1] = BG[1]
    newImage[thres == 0, 2] = BG[2]

    return newImage



def addGrid(image,correlationPlane=False,spacing=75,lw=2):
    """
    Add grid onto the image to help visulize the resutls
    The correlation plane (covolution results) is a special case as we
    need to keep the vmax/vmin of the colorbar unchanged
    """
    newImage=image.copy()
    X = image.shape[0]
    Y = image.shape[1]
    xgrid = np.arange(0,X,spacing)
    ygrid = np.arange(0,Y,spacing)
    
    if len(image.shape) == 3:
        vmax = 255
    else:
        vmax = 1.0

    if correlationPlane:
        vmax = (np.min(image) + (np.max(image)-np.min(image))*0.5)/0.3

    for i in xgrid:
        newImage[i-lw:i+lw,:] = vmax*0.3
    for j in ygrid:
        newImage[:,j-lw:j+lw] = vmax*0.3

    return newImage 


def extractTruthMask(annotateImage):
    """
    Return mask (binary images) showing the position of 
    each cell type from the annotateImage
    """
    colorchannels = {
    'green' : [1],
    'red' : [0],
    'blue': [2],
    'yellow': [0,1],
    'cyan': [1,2],
    }

    masks = dict()
    for i in truthColors.keys():
        mask = np.zeros((annotateImage.shape[0],annotateImage.shape[1]))
        channel = colorchannels[truthColors[i]]
        if len(channel) == 1:
            loc1 = np.equal(annotateImage[:,:,channel[0]],255)
            colorchannelSum = np.sum(annotateImage,axis=2)
            loc2 = np.equal(colorchannelSum,255)
            loc = np.logical_and(loc1,loc2)
            mask[loc] = 1.0
        else:
            print (i,channel[0],channel[1])
            loc1 = np.equal(annotateImage[:,:,channel[0]],255)
            loc2 = np.equal(annotateImage[:,:,channel[1]],255)
            
            mask = np.logical_and(loc1,loc2).astype(np.float)
            
        masks[i] = mask
    
    return masks
    
def load_yaml(yamlFile):
    """
    Load parameters defined in the yaml file
    """

    with open(yamlFile) as f:
        data = yaml.safe_load(f)
    return data

def readInfilters(Params):
    """
    Read in previously generated MACH filters 
    The output is a dict
    """
    filter_dir = Params['FilterDir']
    
    filters = dict()
    for i in Params['FilterNames'].keys():
        filters[i] = dict()
        for j in Params['FilterNames'][i]:
            filter = np.loadtxt(filter_dir+"/"+j+'_filter') # read in ndarray
        
            filters[i][j] = filter
    
    return filters

def readInImages(Params):
    """
    Read in the images that will be used for detection
    If it is validation, also read in the annotated true image
    """
    Images = dict()

    if not os.path.exists(Params['InputImage']):
        raise RuntimeError(f"The input image {Params['InputImage']} does not exist, plz double check the image path")

    image = cv2.imread(Params['InputImage'])
    colorImage = cv2.cvtColor(image,cv2.COLOR_BGR2RGB)
    gray_scale_image = invertGrayImage(colorImage)
    Images['colorImage'] = colorImage
    Images['grayImage'] = gray_scale_image

    if Params['TrueImage'] != None:
    
        if not  os.path.exists(Params['TrueImage']):
            raise RuntimeError(f"The annotated image {Params['TrueImage']} does not exist, plz double check the image path")

        truthImage = cv2.imread(Params['TrueImage'])
        truthImage = cv2.cvtColor(truthImage,cv2.COLOR_BGR2RGB)
        Images['trueImage'] = truthImage
        masks = extractTruthMask(truthImage)
        Images['masks'] = masks
    else:
        Images['trueImage'] = None
        Images['masks'] = None
    
    return Images
 

def areaRefinement(detectedcells, areathres=0.02):
    """
    For each type of detected cells, if the detection are too small, ignore
    Currently the filter size is 75x75, so if the detection is <3% of the size, ignore
    """
    labels, nGroups = measurements.label(detectedcells)
    for i in range(1,nGroups+1):
            if np.sum(detectedcells[labels==i])  <= 75*75*areathres:
                detectedcells[labels == i] = 0.0
    
    return detectedcells

def giveSNR(
        TestImage,
        CrPlanes,
        iters, # array # remove me 
        snrthresh):
    """
    Mask regions where convolutions are greater than snrtresh
    """

    final_results = np.zeros((TestImage.shape[0],TestImage.shape[1]))
    for i in iters:
        [Cr,Crp] = CrPlanes[i] 
        SNR = Cr/Crp
        cells = np.greater(SNR,snrthresh).astype(np.float)                  
        final_results = np.logical_or(final_results,cells).astype(np.float)
    print (snrthresh)
    return final_results


def giveHyp(TestImage,hypfilter,penaltyfilter,\
            iters=[15,30,45,60,75,90,105,120,135,150,165,180],\
            snrthresh=2.0,\
            somaFilter=None, 
            somathres=0.32,
            fragRefine=False,\
            areaRefine=True,\
            areathres = 0.03):
    """
    Rotate the hyp and pennalty filter for each angle in the iters,
    get the SNR and then threshold (snrthres), merge the detected cells at each angle and give the 
    final deteced hyp cells

    The final detected cells will go through two refining processes
    For the fragHypRefine process, a soma only filter is needed, currently, we simply use the amoeboid filter
    For the areaRefine process, we request that the detected cells must have 5% of filter size (75*75*0.05)
    """
    CrPlanes = dict()

    final_results = np.zeros((TestImage.shape[0],TestImage.shape[1]))
    for i in iters:
        rotated_hyp = rotate_image(hypfilter,i)
        rotated_hypp = rotate_image(penaltyfilter,i)
        
        # do convolution
        Cr = ndimage.convolve(TestImage,rotated_hyp)
        Crp = ndimage.convolve(TestImage,rotated_hypp)
        SNR = Cr/Crp
        print ("Iter ", i, " snr ", np.max(SNR))
        CrPlanes[i] = [Cr,Crp]
        hypcells = np.greater(SNR,snrthresh).astype(np.float)
        final_results = np.logical_or(final_results,hypcells).astype(np.float)
    
    # Filtering the resutls
    
    labels, numofgroups = measurements.label(final_results)


    if fragRefine:  
    #1) use the soma filter correlation plane to reduce false positive detection 
    #  (fragmented hyp-like cells) in which two sepearated amoeboid cells 
    #  phypuces a false positive detection 
    #   ooo   ooo    /ooo==ooo\
    #   ooo   ooo    \ooo==ooo/ 
        somaCrPlane = ndimage.convolve(TestImage,somaFilter)
        somaDetected = np.greater(somaCrPlane,somathres).astype(np.float)

        overlap = somaDetected*final_results

    # get the centers of the detection
        labels, nGroups = measurements.label(final_results)
        centers = measurements.center_of_mass(final_results, labels,list(range(1,nGroups+1)))

    # check if the somaDetected overlapped with center of hyp detections
        for i in range(nGroups):
            if overlap[int(centers[i][0]),int(centers[i][1])] == 0:
                final_results[labels == i+1] = 0


    if areaRefine:
        final_results = areaRefinement(final_results)
    # 2) put an area restraint: if the detected area are too small, ignore   
        #for i in range(1,nGroups+1):
            #if np.sum(final_results[labels==i])  <= 75*75*areathres:
                #final_results[labels == i] = 0.0

    return final_results, CrPlanes



def giveRod(TestImage,rodfilter,penaltyfilter,\
            iters=[15,30,45,60,75,90,105,120,135,150,165,180],\
            snrthresh=2.0,\
            somaFilter=None, 
            somathres=0.32,
            fragRefine=False,\
            areaRefine=True,\
            areathres = 0.03):
    """
    Rotate the rod and pennalty filter for each angle in the iters,
    get the SNR and then threshold (snrthres), merge the detected cells at each angle and give the 
    final deteced rod cells

    The final detected cells will go through two refining processes
    For the fragRodRefine process, a soma only filter is needed, currently, we simply use the amoeboid filter
    For the areaRefine process, we request that the detected cells must have 5% of filter size (75*75*0.05)
    """
    CrPlanes = dict()

    final_results = np.zeros((TestImage.shape[0],TestImage.shape[1]))
    for i in iters:
        rotated_rod = rotate_image(rodfilter,i)
        rotated_rodp = rotate_image(penaltyfilter,i)
        
        # do convolution
        Cr = ndimage.convolve(TestImage,rotated_rod)
        Crp = ndimage.convolve(TestImage,rotated_rodp)
        SNR = Cr/Crp
        print ("Iter ", i, " snr ", np.max(SNR))
        CrPlanes[i] = [Cr,Crp]
        rodcells = np.greater(SNR,snrthresh).astype(np.float)
        final_results = np.logical_or(final_results,rodcells).astype(np.float)
    
    # Filtering the resutls
    
    labels, numofgroups = measurements.label(final_results)


    if fragRefine:  
    #1) use the soma filter correlation plane to reduce false positive detection 
    #  (fragmented rod-like cells) in which two sepearated amoeboid cells 
    #  produces a false positive detection 
    #   ooo   ooo    /ooo==ooo\
    #   ooo   ooo    \ooo==ooo/ 
        somaCrPlane = ndimage.convolve(TestImage,somaFilter)
        somaDetected = np.greater(somaCrPlane,somathres).astype(np.float)

        overlap = somaDetected*final_results

    # get the centers of the detection
        labels, nGroups = measurements.label(final_results)
        centers = measurements.center_of_mass(final_results, labels,list(range(1,nGroups+1)))

    # check if the somaDetected overlapped with center of rod detections
        for i in range(nGroups):
            if overlap[int(centers[i][0]),int(centers[i][1])] == 0:
                final_results[labels == i+1] = 0


    if areaRefine:
        final_results = areaRefinement(final_results)

    return final_results, CrPlanes



def giveRam(TestImage,ramfilter,penaltyfilter,\
            iters=[15,30,45,60,75,90,105,120,135,150,165,180],\
            snrthresh=2.0,\
            somaFilter=None, 
            somathres=0.32,
            fragRefine=False,\
            areaRefine=True,\
            areathres = 0.03):
    """
    Rotate the ram and pennalty filter for each angle in the iters,
    get the SNR and then threshold (snrthres), merge the detected cells at each angle and give the 
    final deteced ram cells

    The final detected cells will go through two refining processes
    For the fragRamRefine process, a soma only filter is needed, currently, we simply use the amoeboid filter
    For the areaRefine process, we request that the detected cells must have 5% of filter size (75*75*0.05)
    """
    CrPlanes = dict()

    final_results = np.zeros((TestImage.shape[0],TestImage.shape[1]))
    for i in iters:
        rotated_ram = rotate_image(ramfilter,i)
        rotated_ramp = rotate_image(penaltyfilter,i)
        
        # do convolution
        Cr = ndimage.convolve(TestImage,rotated_ram)
        Crp = ndimage.convolve(TestImage,rotated_ramp)
        SNR = Cr/Crp
        print ("Iter ", i, " snr ", np.max(SNR))
        CrPlanes[i] = [Cr,Crp]
        ramcells = np.greater(SNR,snrthresh).astype(np.float)
        final_results = np.logical_or(final_results,ramcells).astype(np.float)
    
    # Filtering the resutls
    
    labels, numofgroups = measurements.label(final_results)


    if fragRefine:  
    #1) use the soma filter correlation plane to reduce false positive detection 
    #  (fragmented ram-like cells) in which two sepearated amoeboid cells 
    #  pramuces a false positive detection 
    #   ooo   ooo    /ooo==ooo\
    #   ooo   ooo    \ooo==ooo/ 
        somaCrPlane = ndimage.convolve(TestImage,somaFilter)
        somaDetected = np.greater(somaCrPlane,somathres).astype(np.float)

        overlap = somaDetected*final_results

    # get the centers of the detection
        labels, nGroups = measurements.label(final_results)
        centers = measurements.center_of_mass(final_results, labels,list(range(1,nGroups+1)))

    # check if the somaDetected overlapped with center of ram detections
        for i in range(nGroups):
            if overlap[int(centers[i][0]),int(centers[i][1])] == 0:
                final_results[labels == i+1] = 0


    if areaRefine:
        final_results = areaRefinement(final_results)

    return final_results, CrPlanes



def giveDys(TestImage,dysfilter,penaltyfilter,\
            iters=[15,30,45,60,75,90,105,120,135,150,165,180],\
            snrthresh=2.0,\
            somaFilter=None, 
            somathres=0.32,
            fragRefine=False,\
            areaRefine=True,\
            areathres = 0.03):
    """
    Rotate the dys and pennalty filter for each angle in the iters,
    get the SNR and then threshold (snrthres), merge the detected cells at each angle and give the 
    final deteced dys cells

    The final detected cells will go through two refining processes
    For the fragDysRefine process, a soma only filter is needed, currently, we simply use the amoeboid filter
    For the areaRefine process, we request that the detected cells must have 5% of filter size (75*75*0.05)
    """
    CrPlanes = dict()

    final_results = np.zeros((TestImage.shape[0],TestImage.shape[1]))
    for i in iters:
        rotated_dys = rotate_image(dysfilter,i)
        rotated_dysp = rotate_image(penaltyfilter,i)
        
        # do convolution
        Cr = ndimage.convolve(TestImage,rotated_dys)
        Crp = ndimage.convolve(TestImage,rotated_dysp)
        SNR = Cr/Crp
        print ("Iter ", i, " snr ", np.max(SNR))
        CrPlanes[i] = [Cr,Crp]
        dyscells = np.greater(SNR,snrthresh).astype(np.float)
        final_results = np.logical_or(final_results,dyscells).astype(np.float)
    
    # Filtering the resutls
    
    labels, numofgroups = measurements.label(final_results)


    if fragRefine:  
    #1) use the soma filter correlation plane to reduce false positive detection 
    #  (fragmented dys-like cells) in which two sepearated amoeboid cells 
    #  pdysuces a false positive detection 
    #   ooo   ooo    /ooo==ooo\
    #   ooo   ooo    \ooo==ooo/ 
        somaCrPlane = ndimage.convolve(TestImage,somaFilter)
        somaDetected = np.greater(somaCrPlane,somathres).astype(np.float)

        overlap = somaDetected*final_results

    # get the centers of the detection
        labels, nGroups = measurements.label(final_results)
        centers = measurements.center_of_mass(final_results, labels,list(range(1,nGroups+1)))

    # check if the somaDetected overlapped with center of dys detections
        for i in range(nGroups):
            if overlap[int(centers[i][0]),int(centers[i][1])] == 0:
                final_results[labels == i+1] = 0


    if areaRefine:
        final_results = areaRefinement(final_results)

    return final_results, CrPlanes

def giveAmoe(TestImage,amoefilter,penaltyfilter,\
            iters=[15,30,45,60,75,90,105,120,135,150,165,180],\
            snrthresh=2.0,\
            somaFilter=None, 
            somathres=0.32,
            fragRefine=False,\
            areaRefine=True,\
            areathres = 0.03):
    """
    Rotate the amoe and pennalty filter for each angle in the iters,
    get the SNR and then threshold (snrthres), merge the detected cells at each angle and give the 
    final deteced amoe cells

    The final detected cells will go through two refining processes
    For the fragAmoeRefine process, a soma only filter is needed, currently, we simply use the amoeboid filter
    For the areaRefine process, we request that the detected cells must have 5% of filter size (75*75*0.05)
    """
    CrPlanes = dict()

    final_results = np.zeros((TestImage.shape[0],TestImage.shape[1]))
    for i in iters:
        rotated_amoe = rotate_image(amoefilter,i)
        rotated_amoep = rotate_image(penaltyfilter,i)
        
        # do convolution
        Cr = ndimage.convolve(TestImage,rotated_amoe)
        Crp = ndimage.convolve(TestImage,rotated_amoep)
        SNR = Cr/Crp
        print ("Iter ", i, " snr ", np.max(SNR))
        CrPlanes[i] = [Cr,Crp]
        amoecells = np.greater(SNR,snrthresh).astype(np.float)
        final_results = np.logical_or(final_results,amoecells).astype(np.float)
    
    # Filtering the resutls
    
    labels, numofgroups = measurements.label(final_results)


    if fragRefine:  
    #1) use the soma filter correlation plane to reduce false positive detection 
    #  (fragmented amoe-like cells) in which two sepearated amoeboid cells 
    #  pamoeuces a false positive detection 
    #   ooo   ooo    /ooo==ooo\
    #   ooo   ooo    \ooo==ooo/ 
        somaCrPlane = ndimage.convolve(TestImage,somaFilter)
        somaDetected = np.greater(somaCrPlane,somathres).astype(np.float)

        overlap = somaDetected*final_results

    # get the centers of the detection
        labels, nGroups = measurements.label(final_results)
        centers = measurements.center_of_mass(final_results, labels,list(range(1,nGroups+1)))

    # check if the somaDetected overlapped with center of amoe detections
        for i in range(nGroups):
            if overlap[int(centers[i][0]),int(centers[i][1])] == 0:
                final_results[labels == i+1] = 0


    if areaRefine:
        final_results = areaRefinement(final_results)

    return final_results, CrPlanes


def giveSelect(
    TestImage,
    final_results,
    somaFilter,
    somathres,
    fragRefine,
    areaRefine):
    """
    Filter and annotate suprathreshold regions 
    """
    # Filtering the resutls
    labels, numofgroups = measurements.label(final_results)
 
    #1) use the soma filter correlation plane to reduce false positive detection 
    #  (fragmented rod-like cells) in which two sepearated amoeboid cells 
    #  produces a false positive detection 
    #   ooo   ooo    /ooo==ooo\
    #   ooo   ooo    \ooo==ooo/ 
    somaCrPlane = ndimage.convolve(TestImage,somaFilter)
    somaDetected = np.greater(somaCrPlane,somathres).astype(np.float)

    overlap = somaDetected*final_results
    if np.sum(overlap) <= 1:
        print("No Detection with overlapping somas found")
        return overlap
    # get the centers of the detection
    labels, nGroups = measurements.label(final_results)
    centers = measurements.center_of_mass(final_results, labels,list(range(1,nGroups+1)))
    
     
    # check if the somaDetected overlapped with center of rod detections
    #print("centers", centers)
    #print(numofgroups)
    #print(nGroups)
    #print(final_results)
    final = np.zeros_like(final_results)
    for i in range(nGroups):
        #print(centers[i],i)
        try:
            tup = [int(centers[i][0]),int(centers[i][1])]
        except:
            print("WARNING: inf for center. Skipping. Investigate!!")
            continue
        if overlap[int(centers[i][0]),int(centers[i][1])] >= 0:
            final[labels == i+1] = final_results[labels == i+1]
    if np.sum(final) <= 1:
        raise RuntimeError("finalisempty")

    if areaRefine:
        final = areaRefinement(final)
    # 2) put an area restraint: if the detected area are too small, ignore   
        #for i in range(1,nGroups+1):
            #if np.sum(final_results[labels==i])  <= 75*75*areathres:
                #final_results[labels == i] = 0.0

    return final



def giveRamHyp(image,ramp_filter,hypp_filter,rampthres=0.22,hyppthres=0.18):
    """
    give the detected ramified cells and hypertrophic cells 
    based on the hits of ramifiled process filter (ramp) and
    hyertrophic process filter (hypp)
    """

    ramp_hits = ndimage.convolve(image,ramp_filter)
    hypp_hits = ndimage.convolve(image,hypp_filter)
    ramp_detected = np.greater(ramp_hits,rampthres).astype(np.float)
    hypp_detected = np.greater(hypp_hits,hyppthres).astype(np.float)

    # the overlapped area between ramp_detected and hypp_detected are assigned as hyptrophic cells
    # the remaining part in the ramp_detected are ramified cells


    labels, numofgroups = measurements.label(ramp_detected)

    overlap = ramp_detected*hypp_detected

    results = np.ones(ramp_detected.shape)
    for i in np.arange(1,numofgroups+1):
        if np.sum(overlap[labels == i]) != 0:
            results[labels==i] = 0.0

    ram_cells = ramp_detected.copy()
    hyp_cells = np.zeros(ramp_detected.shape)

    ram_cells[results==0] = 0

    hyp_cells[results == 0] = 1

    # area refinement
    ram_cells = areaRefinement(ram_cells)
    hyp_cells = areaRefinement(hyp_cells)
    
    
    return ram_cells, hyp_cells

def giveAmoeDys(image,amoefilter,amoethres=0.22,areathes=20):
    """
    give the detected amoeboid and dystrophic cells 
    based on the convolution hits of amoeboid filter 

    since the amoe and dys filters ahve similar convolution results
    we only use the amoe_hits
    First thres the aomoe hits and discrimnate amoe/dys cells 
    based on area (dys > amoe)
    """
    amoe_hits = ndimage.convolve(image,amoefilter)
    amoe_detected = np.greater(amoe_hits,amoethres).astype(np.float)



    labels, numofgroups = measurements.label(amoe_detected)
    amoe_cells = amoe_detected.copy()
    dys_cells = amoe_detected.copy()

    results = np.ones(amoe_detected.shape)
    for i in np.arange(1,numofgroups+1):
        
        if np.sum(amoe_detected[labels == i]) <= areathes:
            dys_cells[labels == i] = 0.0
        else:
            amoe_cells[labels == i] = 0.0

    # area refinement
    amoe_cells = areaRefinement(amoe_cells)
    dys_cells = areaRefinement(dys_cells)

    return amoe_cells, dys_cells

def removeDetectedCells(TestImage,detected_cells,bgmthres=0.4):
    """
    Remove the detected cells of one filter from the test image so that we can 
    apply the next filter

    TestImage: gray-scale image
    detected_cells: binary image of detected cells using one filter
    bgmthres: thresholding value for cells/background 

    output: new TestImage
    """
    # generate a binary image of the test image
    bimage = np.greater(TestImage,bgmthres).astype(np.float)

    #background gray-scale value
    bgmValue = np.average(TestImage[bimage==0])
    labels, numofgroups = measurements.label(bimage)

    overlap = detected_cells*bimage

    results = np.ones(bimage.shape)
    for i in np.arange(1,numofgroups+1):
        if np.sum(overlap[labels == i]) != 0:
            results[labels==i] = 0.0

    newtestImage = TestImage.copy()
    newtestImage[results==0] = bgmValue
    
    return newtestImage

def getWholeImageResults(allresults,smallImages):
    """
    show the results for whole image detection
    "allresults" a list containt 100 dict oject, each dict object contains
                the detected cell for each type
    "smallImages" the 100 small images by divding the big image
    """
    cases = ['ram','rod','amoe','hyp','dys']
    colors =  {'ram': 'green',
               'rod': 'red',
                'amoe': 'cyan',
                'hyp': 'blue',
                'dys': 'yellow'
                        }
    cellNums = []
    resultsImage = []
    for i in range(len(allresults)):
        tempImage = smallImages[i].copy()
        cellnum = dict()
        for j in cases:
            dumy, nGroup = measurements.label(allresults[i][j])
            cellnum[j] = nGroup
            tempImage = pasteImage(tempImage,allresults[i][j],colors[j])
        resultsImage.append(tempImage)
        cellNums.append(cellnum)
        
    return resultsImage, cellNums


class machPerformance:
    """
    A class to store the peformance of mach filtering
    """
    def __init__(self, mach_results, images):
        """
        The mach_results is a dict that contains the detected_cells by the filtering 
        The "images" is a dict contains the colored image/gray-scale image etc.
        """
        self.detectedCells = mach_results
        self.images = images
        self.masks = self.images['masks']
        self.colorimage = images['colorImage']
        self.CellNums = dict()
        self.TP = dict()
        self.TP_weights = dict()
        self.FP = dict()
        self.FP_weights = dict()
        self.TP_cells = dict()
        self.FP_cells = dict()
        self.PFscore = 0.0
        self.imgResults = dict()
        self.Colors = {'ram': 'green',
                        'rod': 'red',
                        'amoe': 'cyan',
                        'hyp': 'blue',
                        'dys': 'yellow'
                        }
        for i in self.detectedCells.keys():
            self.CellNums[i] = measurements.label(self.detectedCells[i])[1]
    
    def giveImgResutls(self):
        """
        give images show the detection of each cell type
        """
        imgResults = dict()
        for i in self.detectedCells.keys():
            cimage = pasteImage(self.images['colorImage'],self.detectedCells[i],self.Colors[i])
            imgResults[i] = cimage
        self.imgResults = imgResults
        return imgResults

    def resetTPFPWeights(self):
        """
        setting the weights of TP/FP to 1.0
        """
        for cellType in self.detectedCells.keys():
            self.TP_weights[cellType] = 1.0
            self.FP_weights[cellType] = 1.0

    def setTPWeights(self,newTPWeights):

        for cType, newW in newTPWeights.items():
            self.TP_weights[cType] = newW
    
    def setFPWeights(self,newFPWeights):
        for cType, newW in newFPWeights.items():
            self.FP_weights[cType] = newW    
        

    def calculateTPFP(self):
        for cellType, dCells in self.detectedCells.items():
            print (cellType)
            TP_cells, FP_cells, TP, FP, cellNums = getTPFP(dCells,self.masks[cellType],verbose=False,returnOverlap=True)
            self.TP[cellType] = TP
            self.FP[cellType] = FP
            self.TP_cells[cellType] = TP_cells
            self.FP_cells[cellType] = FP_cells
            self.CellNums[cellType] = cellNums
    

    def calculatePFscore(self):
        """
        Calcualte the Performance Criterion based on the TP/FP score
        of each cell type and the associated weights.
        """
        PFscore = 0
        for i in self.detectedCells.keys():
            PFscore += self.TP_weights[i]*(1-self.TP[i]) + self.FP_weights[i]*self.FP[i]

        self.PFscore = PFscore
        return PFscore

    def plotTPFPfigure(self,figname):
        """
        Plot the TP/FP score of each cell type
        """
        annotatedCellNums = dict()
        TPCellNums = dict()
        FPCellNums = dict()

        for cellType in self.detectedCells.keys():
            annotatedCellNums[cellType] = self.CellNums[cellType]['AnnotatedCell']
            TPCellNums[cellType] = self.CellNums[cellType]['TPCells']
            FPCellNums[cellType] = self.CellNums[cellType]['FPCells']

        width=0.4
        barlist1 = plt.bar(np.arange(len(annotatedCellNums.keys())),annotatedCellNums.values(),width=width,alpha=0.3)
        barlist2 = plt.bar(np.arange(len(TPCellNums.keys())),TPCellNums.values(),width=width,alpha=1)
        barlist3 = plt.bar(np.arange(len(FPCellNums.keys()))+width,FPCellNums.values(),width=width,alpha=0.3,hatch="*",ecolor='b')

        for i, j in enumerate(barlist1):
            j.set_color(truthColors[list(annotatedCellNums.keys())[i]])
        for i, j in enumerate(barlist2):
            j.set_color(truthColors[list(TPCellNums.keys())[i]])
        for i, j in enumerate(barlist3):
            j.set_color(truthColors[list(FPCellNums.keys())[i]])

        plt.ylabel('Cell Nums')
        plt.xticks(np.arange(len(annotatedCellNums.keys())),list(annotatedCellNums.keys()))
        lg = plt.legend([barlist1[0],barlist2[0],barlist3[0]],['Annotated Cells','TP Cells','FP Cells'],loc=(1, 0.75))
        plt.savefig(figname,bbox_extra_artists=(lg,), 
            bbox_inches='tight',
            dpi=300)

 # we have 4 data sets for PCA test:
#  1) the synthesized images
#  2) High representative ram/hyptertrophic/rod/dystrophic cells cropped from real image
#     (also contains amoeboid cells, but not considered here)
#  3) Same as 2) but the rod cell are aligned vertically
#  4) Same as 2 but both the rod and hypertrophic cells are vertically aligned
#  4) ~250 Randomly cropped cell, 2) is a subset of 4)

def readPCAcellImages(dataset="synth",plotAllcells=True):
    """
    Read in the cell images that will be used for PCA analysis
    The images are 75x75 pixel
    
            
    dataset = "systh" ; use the synthsize cell images
            = "typical";  use highly representative cell images
            = "random" ; use randomly cropped cell images
            = "rotRodTypical" ; the rod images are vertically aligned
            = "rotRodHyptypical"; both the rod and hypertrophic cells are vertically aligned
    """
    if dataset == "synth":
        imagedir = "./PCAimages/synthe/"
    elif dataset == "typical":
        imagedir = "./PCAimages/typical/"
    elif dataset == "random":
        imagedir = "./PCAimages/real/"
    elif dataset == "rotRodTypical":
        imagedir = "./PCAimages/rotRodtypical/"
    elif dataset == "rotRodHyptypical":
        imagedir = "./PCAimages/rotRodHyptypical/"
        
    allCellImages = [] 
    cellLabels = []
    for i in [a for a  in os.listdir(imagedir) if a[-3:] == "png"]:
        if i[0:1] != "d":
            cellLabels.append(i[0:3])
        else:
            cellLabels.append(i[1:4])
        image = util.ReadImg(imagedir+i).astype(np.uint8)
        image = cleanImage(image,cellThres=100)
        image = invertGrayImage(image)
        allCellImages.append(image)
    
    if plotAllcells:
        displayMultImage(allCellImages)
        
    return allCellImages, cellLabels

def PCAanlysis(cellImages,imagelabel,projtPC=[0,1]):
    """
    Do PCA analyse on the cell images
    
    projtPC = [0,1] --> images are projected on PC1/PC2 plane
    """
    
    # stack images into one array
    total_image = cellImages[0].reshape(75*75)
    for i in np.arange(1, len(cellImages)):
        new = cellImages[i].reshape(75*75)
        total_image = np.vstack((new,total_image))
        
    CellPCA  = PCA()
    CellPCA.fit(total_image)
    projections = CellPCA.transform(total_image)
    
    #k=0
    #plt.figure(dpi=300)
    #for i in np.arange(5):
    #    k+= 1
    #    plt.subplot(1,5,k)
    #    plt.imshow(CellPCA.components_[i].reshape((75,75)),cmap='gray')
    #    plt.xticks([])
    #    plt.yticks([])
    #    plt.title("PC %d \n(%3.2f)" % (k,CellPCA.explained_variance_ratio_[i]),fontsize=7)
    

    #plt.figure(figsize=(3,3),dpi=200)
    #nImage = len(imagelabel) - 1
    #for i,j in enumerate(imagelabel):
    #print (i)
    
        #plt.scatter(projections[nImage-i,projtPC[0]],projections[nImage-i,projtPC[1]],\
                #s=30,color=color[j],alpha=0.5)
    #plt.xlabel('PC1')
    #plt.ylabel('PC2')
    
    
    return CellPCA, total_image


# Now try to manually draw lines to cluster the cells
def returnLines(points):
    """
    Give two points, return a line
    """
    x_coords, y_coords = zip(*points)
    A = np.vstack([x_coords,np.ones(len(x_coords))]).T
    m, c = np.linalg.lstsq(A, y_coords, rcond=None)[0]
    print("Line is y = {m}x + {c}".format(m=m,c=c))

            
