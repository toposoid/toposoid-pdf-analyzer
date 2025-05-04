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
from functools import reduce
from .PdfExtractorCommon import isHeaderOrFooter, getLang, getSentenceSeparator, forcePeriodSpaceSequence, getProtectPeriodIndexRegex, decodeSentence
from .model import PdfTextLine
from .PdfDocumentClassifier import getDocumentFeature
import ToposoidCommon as tc
import copy

LOG = tc.LogUtils(__name__)

def isParagraphHeadUsingRegex(textLine, pdfDocumentBlock, documentFeature):
    """Evaluate whether it is a paragraph boundary using regular expressions

    Args:
        textLine (_type_): _description_
        pdfDocumentBlock (_type_): _description_
        documentFeature (_type_): _description_

    Returns:
        _type_: _description_
    """
    
    check1 = False
    if documentFeature.documentFeatureCondition.isOnlyHeaderLine: 
        #When determining a paragraph, the text information is not included.       
        if isHeadline(pdfDocumentBlock.identifier, documentFeature.isLongProposition(), textLine):
            if documentFeature.isLongProposition():
                for x0 in  documentFeature.getX0ForIndices():
                    if abs(x0 - pdfDocumentBlock.x0) < 5:
                        check1 = True
            else:
                check1 = True                      
    else:
        if pdfDocumentBlock.identifier.startswith("//Document/H") or \
            pdfDocumentBlock.identifier.startswith("//Document/P") or \
            pdfDocumentBlock.identifier.startswith("//Document/L") or \
            re.search("^\/\/Document/Sect.*\/H", pdfDocumentBlock.identifier) or \
            re.search("^\/\/Document/Sect.*\/P", pdfDocumentBlock.identifier) or \
            re.search("^\/\/Document/Sect.*\/L", pdfDocumentBlock.identifier):                                        

            if documentFeature.isLongProposition():
                for x0 in  documentFeature.getX0ForIndices():
                    if abs(x0 - pdfDocumentBlock.x0) < 5:
                        check1 = True
            else:
                check1 = True
        
    if check1:
        #タイトル位置OKの場合、正規表現でさらにチェック
        check2 = documentFeature.isRepresentativeIndex(textLine)
    return check1 and check2

def isParagraphHeadUsingFormat(pageId, prevPageId): 
    """Evaluate whether it is a paragraph boundary using document format

    Args:
        pageId (_type_): _description_
        prevPageId (_type_): _description_

    Returns:
        _type_: _description_
    """
    return not pageId == prevPageId


def isParagraphHead(textLine, documentFeature, pdfDocumentBlock, pageId, prevPageId):
    """Comprehensive judgment of whether it is a boundary between paragraphs
    Args:
        textLine (_type_): _description_
        documentFeature (_type_): _description_
        pdfDocumentBlock (_type_): _description_
        pageId (_type_): _description_
        prevPageId (_type_): _description_

    Returns:
        _type_: _description_
    """
    result = False
    if documentFeature.isPageDivisionTarget():
        result = isParagraphHeadUsingFormat(pageId, prevPageId)
    else:
        result = isParagraphHeadUsingRegex(textLine, pdfDocumentBlock, documentFeature)
    return result

def isHeadline(identifier, isLongProposition, text):    
    
    separator = getSentenceSeparator(getLang(text))
    text = text.strip() + " "
    #If there is a break at the end of the sentence, it is likely to be a sentence.
    if re.search(separator + "$", text):
        return False
    else:
        if identifier.startswith("//Document/H"):              
            return True
        elif re.search("^\/\/Document/Sect.*/H", identifier):
            return True
        #elif not isLongProposition and re.search("^([0-9]+|\([0-9]+?\)|^[0-9]+\)|[①②③④⑤⑥⑦⑧⑨⑩]|[Ⅰ-Ⅹ]+)[\.\-\s].*\s", text):
        #    return True
        else:
            return False

def extractHeadline(text):
    if len(text) > 50:
        regex = re.compile(r"^([0-9]+|\([0-9]+?\)|^[0-9]+\)|[①②③④⑤⑥⑦⑧⑨⑩]|[Ⅰ-Ⅹ]+)([\.\-\s].+?\s.+?\s)(.*)")
        if re.search(regex, text):            
            splitText = re.sub(regex, "\g<3>", text)
            headline = text.replace(splitText, "") 
            return headline, splitText
        else:
            return text, ""
    else:
        return text, ""

def addParagraphIdentifier(text, isPreviousEndOfPeriod):
    """Perform indentation at paragraph boundaries.

    Args:
        text (_type_): 

    Returns:
        _type_: 
    """    
    convertText = " " + text     
    #In the case of heading lines, there are often no full periods. Therefore, take care that the space does not end and the word gets stuck.
    if not convertText.endswith(".") and not convertText.endswith(" "):
        convertText = convertText + " "

    if not isPreviousEndOfPeriod:
        #In the case of a page break, isLongProposition is True, so a paragraph break is included in the page.
        convertText = "~ " + convertText
    return convertText


def markParagraphHeadCandidate(documentInfoOnPage, headerRatio, footerRatio, transversalState):
    """Mark paragraph boundaries

    Args:
        documentInfoOnPage (_type_): _description_
        headerRatio (_type_): _description_
        footerRatio (_type_): _description_
        transversalState (_type_): _description_

    Returns:
        _type_: _description_
    """

    documentFeature = getDocumentFeature(documentInfoOnPage, headerRatio, footerRatio, transversalState) #ドキュメントタイプの取得  
    LOG.info("DocumentFeature:" + documentFeature.__class__.__name__, transversalState)      
    prevPageId = 1
    for pageId, v in documentInfoOnPage.items():
        pdfDocumentBlocks = v[0]
        pageInfo = v[1]        
        isPreviousEndOfPeriod = False
        headlines = []
        for i, pdfDocumentBlock in enumerate(pdfDocumentBlocks):

            #Exclude text that may be included in page headers and footers
            if isHeaderOrFooter(pageInfo.height, headerRatio, footerRatio, pdfDocumentBlock.y0, pdfDocumentBlock.y1):
                continue

            excludeTextLines = list(filter(lambda z: z.fontSize < pageInfo.mainFontSize, pdfDocumentBlock.pdfTextLines))            
            #Determine whether all font sizes are smaller than the main font size and decide whether to import them as text.
            if len(excludeTextLines) == len(pdfDocumentBlock.pdfTextLines):
                continue   
            

            textLine = reduce(lambda x, y: x + y.text, pdfDocumentBlock.pdfTextLines, "")

            lang = getLang(textLine)
            separator = getSentenceSeparator(lang)
            #In Japanese, there is basically no space after the period.
            textLine = forcePeriodSpaceSequence(textLine, documentFeature.isLongProposition(), separator, lang)         

            #Items with wide paragraph spans, such as contracts. → Force paragraph breaks
            if documentFeature.isLongProposition():                
                textLine = textLine.lstrip()

            if isParagraphHead(textLine, documentFeature, pdfDocumentBlock, pageId, prevPageId):

                if not documentFeature.isLongProposition() and re.search("^" + getProtectPeriodIndexRegex() + "$", textLine):                                            
                    #For index heading-only text, fill in the space on the right without protecting the period. 
                    #Maybe it's okay to protect it。
                    #Keep the space on the left as it affects paragraph division.
                    convertText = textLine.rstrip()
                
                convertText = addParagraphIdentifier(textLine, isPreviousEndOfPeriod)

                if isHeadline(pdfDocumentBlock.identifier, documentFeature.isLongProposition(), textLine.strip()):
                    headline, mainText =  extractHeadline(decodeSentence(textLine.strip()))
                    headlines.append(headline)
                    convertText = "~  " + mainText
                                
                fontSize = pdfDocumentBlock.pdfTextLines[0].fontSize                
                pdfDocumentBlock.pdfTextLines[0] = PdfTextLine(text = convertText, fontSize = fontSize)    
            else:
                                
                convertText = textLine                
                if not documentFeature.isLongProposition(): #if paragraphs containing many sentences are not allowed, create paragraphs even in blocks.
                    #For index only, space is taken at the end of the line without indentation.
                    #The reason for doing this is that ".+space" basically separates sentences.
                    if re.search("^" + getProtectPeriodIndexRegex() + "$", textLine):
                        #For index heading-only text, fill in the space on the right without protecting the period. 
                        #Maybe it's okay to protect it。
                        #Keep the space on the left as it affects paragraph division.
                        convertText = convertText.rstrip()
                    else:
                        #TODO:ブロック単位でパラグラフを形成(ただし、ページ区切りを注意する)                        
                        convertText = addParagraphIdentifier(convertText, True)

                fontSize = pdfDocumentBlock.pdfTextLines[0].fontSize   
                #TODO:headlineををBlockからぬく
                if isHeadline(pdfDocumentBlock.identifier, documentFeature.isLongProposition(), textLine.strip()):
                    headline, mainText =  extractHeadline(decodeSentence(textLine.strip()))
                    headlines.append(headline)
                    pdfDocumentBlock.pdfTextLines[0] = PdfTextLine(text = mainText, fontSize = fontSize)
                else:
                    pdfDocumentBlock.pdfTextLines[0] = PdfTextLine(text = convertText, fontSize = fontSize)
                
            #If the end of one block does not end with a period, transmit that status to the next block.
            if re.search(separator + "$", convertText):
                isPreviousEndOfPeriod = True
            else:
                isPreviousEndOfPeriod = False
     
            prevPageId = pageId    
        pageInfo.headlines = copy.copy(headlines)
        

    return documentInfoOnPage, documentFeature.isPageDivisionTarget()