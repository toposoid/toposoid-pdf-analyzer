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

from .PdfExtractorCommon import linkLabelAndContent, isHeaderOrFooter, convertJpeg
from PIL import ImageStat, Image
import shutil
import numpy as np
import pandas as pd
import copy
from pathlib import Path

def checkEmptyData(df, path):
    """Normalizing table data_summary_

    Args:
        df (_type_): pandas dataflame
        path (_type_): 

    Returns:
        _type_: 
    """
    if df is None:
        return False, None
    for columnName in list(df.columns.values):
        #ref. https://qiita.com/Kent-747/items/08c1f5c642d4e2c7324c
        df[columnName] = df[columnName].fillna(method='ffill') #Handling merged cells
        df[columnName] = df[columnName].astype(str) #Cast to string type
        df[columnName] = df[columnName].replace("_x000D_", "", regex=True) #Remove CRCF code from Excel
        df[columnName] = df[columnName].str.strip() #Space Removal
        df[columnName] = df[columnName].replace("\t", " ", regex=True) #Since the output is tab-delimited, tabs are converted to spaces.
        df[columnName] = df[columnName].replace("\n", "", regex=True) #If there is a newline, convert it to an empty string
        df[columnName] = df[columnName].replace("", np.nan) #Convert empty strings to NA
    #Remove all NA columns
    df = df.dropna(how='all', axis=1)
    ##Remove all NA rows
    df = df.dropna(how='all')
    if len(df) == 1 or len(df.columns) == 0:
        return False, None
    #Convert to TSV file
    tsvFilePath = path + ".tsv"
    parquetFilePath = path + ".parquet"
    df.to_csv(tsvFilePath, index = False, sep='\t', encoding="utf-8") 
    df.to_parquet(parquetFilePath, index=False)
    return True, df


def isValidContent(pageInfo, content, headerRatio, footerRatio, isImage, pdfDocumentBlock):
    """Evaluate appropriate image or table data

    Args:
        pageInfo (_type_): PATH elements present in the PDF Extract API output
        content (_type_): PdfContentsInfo Object
        headerRatio (_type_): 
        footerRatio (_type_): 
        isImage (bool): True if the content is an image
        pdfDocumentBlock (_type_): PdfDocumentBlock Object

    Returns:
        _type_: 
    """
    #If headerRatio == 0 and footerRatio == 0, the full image and full table will be available.
    if (not headerRatio == 0) and  (not footerRatio == 0):
        if isHeaderOrFooter(pageInfo.height, headerRatio, footerRatio, content.coodinate.y0, content.coodinate.y1):
            return False
        
    if isImage:
        #If an image overlaps with a text area, the text area takes priority.
        #Compare the area of ​​the image area to the area of ​​the text area
        if pdfDocumentBlock is not None:
            sContent = abs(content.coodinate.y1 - content.coodinate.y0) * abs(content.coodinate.x1 - content.coodinate.x0)            
            sText = abs(pdfDocumentBlock.y1 - pdfDocumentBlock.y0) * abs(pdfDocumentBlock.x1 - pdfDocumentBlock.x0)
            if abs(sContent - sText) < 10 and len(pdfDocumentBlock.pdfTextLines[0].text) > 100: #面積の差分がほとんどなく、テキスト文字数が多い場合は、画像はほとんどテキストであるということになる。
                return False

        #Images with abnormal aspect ratios will be excluded.
        ratio = abs(content.coodinate.y1 - content.coodinate.y0)/abs(content.coodinate.x1 - content.coodinate.x0)
        if ratio < 1/20 or ratio > 20:
            return False

        image = Image.open(content.path)
        stat = ImageStat.Stat(image)
        #Single color images are excluded
        if len(list(filter(lambda x: int(x) == 0, stat.var[0:3]))) == 0:
            return True
        else:
            return False

    else:
        isOk, df = checkEmptyData(pd.read_excel(content.path, header = None), content.path)
        if isOk:
            return True
        else:
            return False

def changePath(content, documentId):
    """Deploy the contents of the tmp directory under the contents directory.

    Args:
        content (_type_): PdfContentsInfo Object
        documentId (_type_): 

    Returns:
        _type_: 
    """
    subDirname = ""
    if content.contentType.startswith("IMAGE"):        
        subDirname = "images"
        originalFilename = Path(content.path).stem
        ext = content.path.split(".")[-1]    
        #Copy Original
        shutil.copy(content.path, "contents/%s/%s!%s.%s" % (subDirname, content.id, originalFilename, ext))
        #Move JPEG
        targetFile, width, height = convertJpeg(content.path, content.id, "tmp/%s/" % (documentId))
        shutil.move(targetFile, "contents/%s/%s.jpg" % (subDirname, content.id))
    else:
        subDirname = "tables"
        originalFilename = Path(content.path).stem
        ext = content.path.split(".")[-1]    
        #Move Original
        shutil.move(content.path, "contents/%s/%s!%s.%s" % (subDirname, content.id, originalFilename, ext))
        #Mone Parquet
        targetFile = content.path + ".parquet"
        shutil.move(targetFile, "contents/%s/%s.parquet" % (subDirname, content.id))
        #Mone TSV
        targetFile = content.path + ".tsv"
        shutil.move(targetFile, "contents/%s/%s.tsv" % (subDirname, content.id))
    
    #Move the original file
    #if os.path.isfile(content.path):
    #    shutil.move(content.path, "contents/%s/%s.%s" % (subDirname, id, ext))  

    ext = targetFile.split(".")[-1]    
    content.path = "contents/%s/%s.%s" % (subDirname, content.id, ext)
    return content

def chooseContents(documentId, pageInfo, contentsInfo, headerRatio, footerRatio, isImage, pdfDocumentBlock):
    """Scanning and filtering appropriate image and table data

    Args:
        documentId (_type_): 
        pageInfo (_type_): PATH elements present in the PDF Extract API output
        contentsInfo (_type_): PdfContentsInfo Object
        headerRatio (_type_): 
        footerRatio (_type_): 
        isImage (bool): True if the content is an image
        pdfDocumentBlock (_type_): PdfDocumentBlock Object

    Returns:
        _type_: 
    """
    #Remove images and tables that seem to contain little information. Remove images that overlap with text.
    contentsInfo = list(filter(lambda x: isValidContent(pageInfo, x, headerRatio, footerRatio, isImage, pdfDocumentBlock), contentsInfo))    
    #Confirm the path.
    contentsInfo = list(map(lambda x: changePath(x, documentId), contentsInfo))
    return contentsInfo

def getContentListWithLabel(contentDict, labels):
    """Attaching labels to images and table data

    Args:
        contentDict (_type_): 
        labels (_type_): 

    Returns:
        _type_: 
    """
    upperUsedLabels = []
    lowerUsedLabels = []
    upperTmpUsedLabels = []
    lowerTmpUsedLabels = []
    prevPageId = -1
    
    upperInfoDict = {}
    lowerInfoDict = {}

    adoptedUpperDistanceList = []
    adoptedLowerDistanceList = []

    for pageId, images in contentDict.items():

        for content in images:                
            if not pageId == prevPageId:
                upperUsedLabels = copy.copy(upperTmpUsedLabels)
                lowerUsedLabels = copy.copy(lowerTmpUsedLabels)
                #tmpUsedLabels = usedLabels
            coodinate = content.coodinate
            upperLabel, upperMetaList, upperDistance = linkLabelAndContent(pageId, coodinate, labels, upperUsedLabels, True, content.page.convergenceRadius)
            lowerLabel, lowerMetaList, lowerDistance = linkLabelAndContent(pageId, coodinate, labels, lowerUsedLabels, False, content.page.convergenceRadius)            

            if not upperLabel == "" and not upperLabel in upperTmpUsedLabels:
                upperTmpUsedLabels.append(upperLabel)
            if not lowerLabel == "" and not lowerLabel in lowerTmpUsedLabels:
                lowerUsedLabels.append(lowerLabel)

            upperInfoDict[content.id] = (upperLabel, upperMetaList, upperDistance)
            lowerInfoDict[content.id] = (lowerLabel, lowerMetaList, lowerDistance)

            if upperDistance == lowerDistance:
                adoptedUpperDistanceList.append(True)
                adoptedLowerDistanceList.append(True)
            else:
                if upperDistance < lowerDistance:
                    adoptedUpperDistanceList.append(True)
                else:
                    adoptedLowerDistanceList.append(True)

            prevPageId = pageId

    infoDict = {}
    if len(adoptedUpperDistanceList) > len(adoptedLowerDistanceList):
        infoDict = upperInfoDict
    else:
        infoDict = lowerInfoDict

    contentList = []
    for pageId, images in contentDict.items():
        for content in images:                
            #If no label is associated with it, it will be an empty string.
            content.label = infoDict[content.id][0]
            #If no label is associated with it, it will be an empty list.
            content.metaList = infoDict[content.id][1]
            contentList.append(content)
    return contentList

def getSelectdContents(documentId, headerRatio, footerRatio, documentInfoOnPage, imagesDict, tablesDict, labels):
    """Scan and filter image and table data

    Args:
        documentId (_type_): 
        headerRatio (_type_): 
        footerRatio (_type_): 
        documentInfoOnPage (_type_): 
        imagesDict (_type_): 
        tablesDict (_type_): 
        labels (_type_): 

    Returns:
        _type_: 
    """
    selectedImagesDict = {}
    selectedTablesDict = {}
    
    #Remove and label inappropriate content page by page
    for pageId, v in documentInfoOnPage.items():
        pdfDocumentBlocks = v[0]
        pageInfo = v[1]
        pdfDocumentBlock = None
        if len(pdfDocumentBlocks) > 0:
            #When using the Adobe parser, there is only one pdfDocumentBlocks element.
            pdfDocumentBlock = pdfDocumentBlocks[0]
        
        if pageId in imagesDict and len(imagesDict[pageId]) > 0:
            selectedImagesDict[pageId] = chooseContents(documentId, pageInfo, imagesDict[pageId], headerRatio, footerRatio, True, pdfDocumentBlock)
        if pageId in tablesDict and len(tablesDict[pageId]) > 0:
            selectedTablesDict[pageId] = chooseContents(documentId, pageInfo, tablesDict[pageId], headerRatio, footerRatio, False, pdfDocumentBlock)

    imageList = getContentListWithLabel(selectedImagesDict, labels)
    tableList = getContentListWithLabel(selectedTablesDict, labels)

    return imageList, tableList
