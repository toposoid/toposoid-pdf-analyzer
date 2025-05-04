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

from .DocumentFeatureJapaneseLegal import DocumentFeatureJapaneseLegal
from .DocumentFeatureEnglishLegal import DocumentFeatureEnglishLegal
from .DocumentFeatureGeneral import DocumentFeatureGeneral
from .DocumentFeaturePresentation import DocumentFeaturePresentation
from .DocumentFeatureOther import DocumentFeatureOther
import re
from functools import reduce
from .PdfExtractorCommon import isHeaderOrFooter
import ToposoidCommon as tc

LOG = tc.LogUtils(__name__)

documentFeatures = [    
    DocumentFeatureJapaneseLegal(), 
    DocumentFeatureEnglishLegal(),
    DocumentFeatureGeneral(),
    DocumentFeaturePresentation(),
    DocumentFeatureOther(),
]

def isCaptionIdentifier(identifier):
    """Evaluate if text is a caption

    Args:
        identifier (_type_): PATH elements present in the PDF Extract API output

    Returns:
        _type_: 
    """
    if identifier.startswith("//Document/H"):
        return True 
    elif identifier.startswith("//Document/L"):
        return True
    elif re.search("^\/\/Document/Sect.*/H", identifier):
        return True
    elif re.search("^\/\/Document/Sect.*/L", identifier):
        return True
    if identifier.startswith("//Document/Title"):
        return True     
    if identifier.startswith("//Document/Sect/Title"):
        return True     
    else:
        return False


def getDocumentFeature(documentInfoOnPage, headerRatio, footerRatio, transversalState):
    """Evaluate document characteristics from PDF content.Returns the identified DocumentFeature object.

    Args:
        documentInfoOnPage (_type_): 
        headerRatio (_type_): 
        footerRatio (_type_): 

    Returns:
        _type_: 
    """
    
    indexMatchs = {}
    captionMatchs = {}

    documerntFeaturesSamePriority = []
    prevPriority = 0
    for documentFeature in sorted(documentFeatures, key=lambda x: x.getPriority()): #Sorting with priority
    
        if documentFeature.isPageDivisionTarget():
            hitResults = []
            for pageId, v in documentInfoOnPage.items():
                pdfDocumentBlocks = v[0]
                pageInfo = v[1]  
                hitResults.append(documentFeature.checkPageDivisionTarget(pageInfo))

            #If more than 80% of the results are True, use this documentFeature.
            if len(list(filter(lambda x: x, hitResults)))/ len(hitResults) > 0.8:
                return documentFeature  
        else:

            if not prevPriority == documentFeature.getPriority():
                #Among items with the same priority, select the one with the highest index matching frequency.
                if len(documerntFeaturesSamePriority) > 0:
                    return sorted(documerntFeaturesSamePriority, key=lambda x: x.getFrequencyForIndex(), reverse=True)[0]
                documerntFeaturesSamePriority = []

            featureName = documentFeature.__class__.__name__
            indexMatchs[featureName] = False
            captionMatchs[featureName] = False

            for pageId, v in documentInfoOnPage.items():
                pdfDocumentBlocks = v[0]
                pageInfo = v[1]  
                #check titleOfTopPage
                if documentFeature.isCaptionMatch(pageInfo.titleOfTopPage):
                    captionMatchs[featureName] = True
                for i, pdfDocumentBlock in enumerate(pdfDocumentBlocks):

                    #Check header text block only
                    if not isCaptionIdentifier(pdfDocumentBlock.identifier):
                        continue

                    #Exclude text that may be included in page headers or footers
                    if isHeaderOrFooter(pageInfo.height, headerRatio, footerRatio, pdfDocumentBlock.y0, pdfDocumentBlock.y1):
                        continue

                    excludeTextLines = list(filter(lambda z: z.fontSize < pageInfo.mainFontSize, pdfDocumentBlock.pdfTextLines))            
                    #Determine whether all font sizes are smaller than the main font size and whether to import them as text.
                    if len(excludeTextLines) == len(pdfDocumentBlock.pdfTextLines):
                        continue   
                    
                    textLine = reduce(lambda x, y: x + y.text, pdfDocumentBlock.pdfTextLines, "")
                    
                    if documentFeature.isIndexMatch(textLine, pdfDocumentBlock.x0):      
                        indexMatchs[featureName] = True
                                
                    if documentFeature.isCaptionMatch(textLine):      
                        captionMatchs[featureName] = True


            if indexMatchs[featureName] and captionMatchs[featureName]:
                condition, coordinates, freq = documentFeature.getRegexAndCoordinateAndFrequencyForIndex()
                freqCaption = documentFeature.getFrequencyForCaption()
                priority = documentFeature.getPriority()
                isLongProposition = documentFeature.isLongProposition()
                if freq > 1:
                    LOG.info(f"feature name: {featureName}", transversalState)
                    LOG.info(f"regex: {condition.regex})", transversalState)
                    LOG.info(f"coordinates: {coordinates}", transversalState)
                    LOG.info(f"frequency: {freq}", transversalState)
                    LOG.info(f"caption: {freqCaption}", transversalState)
                    LOG.info(f"priority: {priority}", transversalState)
                    LOG.info(f"isLongProposition: {isLongProposition}", transversalState)
                    LOG.info(f"X0ForIndices: {documentFeature.getX0ForIndices()}", transversalState)
                    documerntFeaturesSamePriority.append(documentFeature)

                #The most common feature of the above statistics is the document's characteristic.
                #Regarding indexing, we also pay attention to how many x0 coordinates are to the left.
                #However, this will be done with consideration of priorities.

            prevPriority = documentFeature.getPriority()
    
    if len(documerntFeaturesSamePriority) > 0:
        return sorted(documerntFeaturesSamePriority, key=lambda x: x.getFrequencyForIndex(), reverse=True)[0]
    else:
        return DocumentFeatureOther()

