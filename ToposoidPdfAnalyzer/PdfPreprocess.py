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

from .PdfExtractorCommon import selectValidSentence, extractPageBreak
from .PdfAnalyzeAdobeJson import analyzePdfJson
from .PdfExtractorFromRawData import PdfExtractorFromRawData
import shutil
import os
from .PdfReferenceExtractor import getReference
from .PdfParagraphHeadExtractor import markParagraphHeadCandidate
from .PdfTableOfContentsExtractor import getTableOfContents
from .PdfContentsSelector import getSelectdContents

def removeTempDir(documentId):
    """Cleaning the temporary directory
    """
    if os.path.isdir("tmp/" + documentId):
        shutil.rmtree("tmp/" + documentId)


def preprocess(documentId, filename, headerRatio, footerRatio, transversalState):
    """preprocess

    Args:
        documentId (_type_): _description_
        filename (_type_): _description_
        headerRatio (_type_): _description_
        footerRatio (_type_): _description_
        transversalState (_type_): _description_

    Returns:
        _type_: _description_
    """
    PdfExtractorFromRawData(documentId, filename)
    documentInfoOnPage, imagesDict, tablesDict, labels = analyzePdfJson(documentId, f"tmp/{documentId}/structuredData.json")
    
    #Scrutinizing the document
    documentInfoOnPage = getTableOfContents(documentInfoOnPage, headerRatio, footerRatio) #Get table of contents
    documentInfoOnPage = getReference(documentInfoOnPage, headerRatio, footerRatio) #Get reference
    documentInfoOnPage = selectValidSentence(documentInfoOnPage, headerRatio, footerRatio) #Mainly removing table element text (processed at this position because the above may be a table)
    documentInfoOnPage = extractPageBreak(documentInfoOnPage, headerRatio, footerRatio)#Add page spanning information
    documentInfoOnPage, isPageDivisionTarget = markParagraphHeadCandidate(documentInfoOnPage, headerRatio, footerRatio, transversalState) #Obtaining heading information (paragraph boundaries)

    #Examine content information for each page
    imageList, tableList = getSelectdContents(documentId, headerRatio, footerRatio, documentInfoOnPage, imagesDict, tablesDict, labels)
    #Cleaning the temporary directory
    removeTempDir(documentId)
    return documentInfoOnPage, imageList, tableList, isPageDivisionTarget

def preprocessForTest(documentId, headerRatio, footerRatio, transversalState):
    """preprocess for Test.

    Args:
        documentId (_type_): _description_
        headerRatio (_type_): _description_
        footerRatio (_type_): _description_
        transversalState (_type_): _description_

    Returns:
        _type_: _description_
    """
    documentInfoOnPage, imagesDict, tablesDict, labels = analyzePdfJson(documentId, f"tmp/{documentId}/structuredData.json")
    
    #Scrutinizing the document
    documentInfoOnPage = getTableOfContents(documentInfoOnPage, headerRatio, footerRatio) #Get table of contents
    documentInfoOnPage = getReference(documentInfoOnPage, headerRatio, footerRatio) #Get reference
    documentInfoOnPage = selectValidSentence(documentInfoOnPage, headerRatio, footerRatio) #Mainly removing table element text (processed at this position because the above may be a table)
    documentInfoOnPage = extractPageBreak(documentInfoOnPage, headerRatio, footerRatio)#Add page spanning information
    documentInfoOnPage, isPageDivisionTarget = markParagraphHeadCandidate(documentInfoOnPage, headerRatio, footerRatio,transversalState) #Obtaining heading information (paragraph boundaries)

    #Examine content information for each page
    imageList, tableList = getSelectdContents(documentId, headerRatio, footerRatio, documentInfoOnPage, imagesDict, tablesDict, labels)
    #Cleaning the temporary directory
    removeTempDir(documentId)
    return documentInfoOnPage, imageList, tableList, isPageDivisionTarget
