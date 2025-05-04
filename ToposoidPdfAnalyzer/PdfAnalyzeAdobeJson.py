'''
  Copyright (C) 2025  Linked Ideal LLC.[https://linked-ideal.com/]
 
  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU Affero General Public License as
  published by the Free Software Foundation, version 3.
 
  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU Affero General Public License for more details.
 
  You should have received a copy of the GNU Affero General Public License
  along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import re
from .model import PdfPageInfo, PdfContentsInfo, PdfContentsCoodinate, PdfTextLine, PdfDocumentBlock
from .PdfExtractorCommon import getLabels, existLabel, preprocessText
import uuid
import json
from functools import reduce

CONVERGENCE_RADIUS = 150

def convertCoodinate(bounds, isUpperOrigin, heightOfPage):
    """Transform the coordinates so that the origin is LeftTop
    In PostScript, the bottom left corner of the MediaBox or CropBox is the origin (0,0) of user space, but in PDF, the bottom left corner of the MediaBox or CropBox is not necessarily the origin (0,0).
    ref.https://www.antenna.co.jp/pdf/reference/pdf-point.html

    Args:
        bounds (_type_): Box coordinates
        isUpperOrigin (bool): True if the origin is at LeftTop
        heightOfPage (_type_): Page Height

    Returns:
        _type_: 
    """
    if isUpperOrigin:
        return PdfContentsCoodinate(x0=bounds[0], x1=bounds[2], y0=bounds[1], y1=bounds[3])
    else:    
        return PdfContentsCoodinate(x0=bounds[0], x1=bounds[2], y0=heightOfPage-bounds[3], y1=heightOfPage-bounds[1])
    

def isUpperOrigin(coodinate, heightOfPage):
    """Predict the position of the origin based on whether the y0 coordinate of the first element on the page is above or below half the page height.

    Args:
        coodinate (_type_): 
        heightOfPage (_type_): 

    Returns:
        _type_: 
    """    
    if coodinate[1] > heightOfPage / 2:
        return False
    else:
        return True

def analyzePdfJson(documentId, filename):
    """Parse structuredData.json, the output of the PDF Extract API.

    Args:
        documentId (_type_): 
        filename (_type_): 

    Returns:
        _type_: 
    """    
    textInfoDict = {}
    with open(filename, "r") as f: 
        result = json.load(f)    

        #Determine the main font size for each page, the title of the entire document, and coordinate correction information.
        textSizeDict = {}
        firstElementCoodinateDict = {}   
        prevPageId = 0     
        titleOfTopPage = ""
        for element in result["elements"]:

            #Sometimes there are elements such as Table elements that do not have a Page.
            if "Page" in element:
                pageId = element["Page"] + 1
                if not pageId == prevPageId:
                    if "Bounds" in element:
                        firstElementCoodinateDict[pageId] = element["Bounds"]

            if "Text" in element:                
                fontSize = int(element["TextSize"])          
                if titleOfTopPage == "":
                    if "Path" in element:
                        if element["Path"].startswith("//Document/Title") or element["Path"].startswith("//Document/Sect/Title"): 
                            titleOfTopPage = element["Text"]
                if pageId in textSizeDict:
                    if fontSize in textSizeDict[pageId]:
                        textSizeDict[pageId][fontSize] += len(element["Text"])
                    else:
                        textSizeDict[pageId][fontSize] = len(element["Text"])
                else:
                    textSizeDict[pageId] = {fontSize:len(element["Text"])}

                prevPageId = pageId
        #Creating page information
        pageInfoDict = {}
        for page in result["pages"]:     
            pageId = page["page_number"] + 1  
            mainFontSize = -1
            if pageId in textSizeDict:
                #Select the TextSize with the most characters per page as the main text size
                mainFontSize = sorted(textSizeDict[pageId].items(), key = lambda x : x[1], reverse = True)[0][0]
            pageInfoDict[pageId] = PdfPageInfo(pageId=pageId, width=page["width"], height=page["height"], mainFontSize=mainFontSize,  convergenceRadius=CONVERGENCE_RADIUS, representativePoints=[], titleOfTopPage=titleOfTopPage)

        pdfDocumentBlocksDict= {}
        labels = []
        imagesDict = {}
        tablesDict = {}        
        
        for element in result["elements"]:
            
            if element["Path"].startswith("//Document/Title") or element["Path"].startswith("//Document/Sect/Title"):
                if element["Text"] == titleOfTopPage:
                    #Document titles are treated as non-text
                    continue

            #Sometimes there are elements such as Table elements that do not have a Page.
            if "Page" in element:
                pageId = element["Page"] + 1
                bounds = element["Bounds"]  
                upperOrigin = isUpperOrigin(firstElementCoodinateDict[pageId], pageInfoDict[pageId].height) 

            if "Text" in element:
                texts = PdfTextLine(text=preprocessText(element["Text"]), fontSize=element["TextSize"]) 

                coodinate = convertCoodinate(bounds, upperOrigin, pageInfoDict[pageId].height)
                pdfDocumentBlock = PdfDocumentBlock(pdfTextLines=[texts], x0=coodinate.x0, x1=coodinate.x1, y0=coodinate.y0, y1=coodinate.y1, pageId = pageId, identifier=element["Path"]) 
                if pageId in pdfDocumentBlocksDict:
                    pdfDocumentBlocksDict[pageId].append(pdfDocumentBlock)
                else:
                    pdfDocumentBlocksDict[pageId] = [pdfDocumentBlock]     
                #If there are any candidates for labels, obtain them.
                if existLabel(element["Text"], True):
                    #Since one text may have multiple labels
                    for label in getLabels(element["Text"].strip(), True):   
                        contentInfo = PdfContentsInfo(id=str(uuid.uuid1()), label=label, contentType="CAPTION", path="", page=pageInfoDict[pageId], coodinate=coodinate, metaList=[element["Text"].strip()], identifier=element["Path"])
                        labels.append(contentInfo)

            elif "Path" in element:
                #//Document/L[7]/LI/LBody/Figure ch a pattern also exists
                if element["Path"].startswith("//Document/Figure") or re.search("^\/\/Document\/.*Figure", element["Path"]):
                    if "filePaths" in element:
                        #In this case, an image can be obtained. However, there may be multiple images.
                        for filepath in element["filePaths"]:
                            if "Page" in element and "Bounds" in element:                            
                                path = f"tmp/{documentId}/{filepath}"
                                pageId = element["Page"] + 1
                                bounds = element["Bounds"]
                                coodinate = convertCoodinate(bounds, upperOrigin, pageInfoDict[pageId].height)                        
                                pdfContentInfo = PdfContentsInfo(id=str(uuid.uuid1()), contentType="IMAGE", label="", path=path, page=pageInfoDict[pageId], coodinate=coodinate, identifier=element["Path"])
                                #The labels will be added later.
                                if pageId in imagesDict:
                                    imagesDict[pageId].append(pdfContentInfo)
                                else:
                                    imagesDict[pageId] = [pdfContentInfo]                        
                if element["Path"].startswith("//Document/Table") or re.search("^\/\/Document\/.*Table", element["Path"]):
                    if "filePaths" in element:
                        #In this case, you can get a table. However, there may be multiple tables.
                        #Even the table path may be an image file, so remove it.
                        for filepath in list(filter(lambda x: x.endswith("xlsx"), element["filePaths"])):
                            if "Page" in element and "Bounds" in element:
                                path = f"tmp/{documentId}/{filepath}"
                                pageId = element["Page"] + 1
                                bounds = element["Bounds"]
                                coodinate = convertCoodinate(bounds, upperOrigin, pageInfoDict[pageId].height)
                                pdfContentInfo = PdfContentsInfo(id=str(uuid.uuid1()), contentType="TABLE", label="", path=path, page=pageInfoDict[pageId], coodinate=coodinate, identifier=element["Path"])
                                #The labels will be added later.
                                if pageId in tablesDict:
                                    tablesDict[pageId].append(pdfContentInfo)
                                else:
                                    tablesDict[pageId] = [pdfContentInfo]                        

        for pageId, pdfDocumentBlocks in pdfDocumentBlocksDict.items():            
            textInfoDict[pageId] = (pdfDocumentBlocks, pageInfoDict[pageId])

        return textInfoDict, imagesDict, tablesDict, labels

    
