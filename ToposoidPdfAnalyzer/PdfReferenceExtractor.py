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
from .PdfExtractorCommon import isHeaderOrFooter
import copy
import unicodedata
from .model import PdfDocumentBlock

def getSentence(foundRefHead, pdfDocumentBlock, prevFontSize, sentence,blockNoList, N=10):
    """Get reference text

    Args:
        foundRefHead (_type_): _description_
        pdfDocumentBlock (_type_): _description_
        prevFontSize (_type_): _description_
        sentence (_type_): _description_
        blockNoList (_type_): _description_
        N (int, optional): _description_. Defaults to 10.

    Returns:
        _type_: _description_
    """
    
    isReset = False
    isSpanOut = False
    textLine = reduce(lambda x, y: x + y.text.replace("\n", ""), pdfDocumentBlock.pdfTextLines, "")
    fontSize = pdfDocumentBlock.pdfTextLines[0].fontSize #Compare by font size at the beginning of the line
    regexSpanOutPattern1 = re.compile("^.*(references|参考|文献|参照).*")
    regexSpanOutPattern2 = re.compile("^(\[1\]|\(1\)|（1）|1[\)|\[1）|\.|\s|　]).*")
    #textLine = unicodedata.normalize('NFKC', textLine).lower()
    isSpanOuts =[
        re.search(regexSpanOutPattern1, unicodedata.normalize('NFKC', textLine.strip()).lower()),
        re.search(regexSpanOutPattern2, textLine),        
    ]
    isSpanOut = reduce(lambda x, y: x or y, isSpanOuts)
    #When the reference heading appears, the analysis ends.
    if isSpanOut:
        return textLine.strip() + sentence, blockNoList, fontSize, isReset, isSpanOut

    if (not foundRefHead) and (len(blockNoList) > N):
        #After detecting the end of the reference analysis start line, if the beginning of the line cannot be confirmed within the specified number of lines, reset the reference analysis.
        sentence = textLine.strip()
        blockNoList = []    
        isReset = True
    elif abs(fontSize - prevFontSize) > 3.0:
        #If the font size changes significantly, the accumulated text will be discarded.
        sentence = textLine.strip()
        blockNoList = []
        isReset = True
    elif pdfDocumentBlock.identifier.startswith("//Document/H") or re.search("^\/\/Document\/Sect.*\/H", pdfDocumentBlock.identifier):
        #Reset if Block has a heading
        sentence = ""
        blockNoList = []
        isReset = True
    elif len(blockNoList) == 0:
        if len(sentence.strip()) == 0:
            sentence = textLine.strip()
        else:
            #If there are any sentences that span pages, leave them in the sentence.
            sentence = textLine + sentence            
    else:
        sentence = textLine + sentence                         
            
    return sentence, blockNoList, fontSize, isReset, isSpanOut


def haveReferenceTitle(documentInfoOnPage, headerRatio, footerRatio):
    """Check for existence of reference heading title

    Args:
        documentInfoOnPage (_type_): _description_
        headerRatio (_type_): _description_
        footerRatio (_type_): _description_

    Returns:
        _type_: _description_
    """
    existReferenceTitle = False
    existStartPattern = False
    referenceTitlePage = -1
    regexTitlePattern = re.compile("^.*(references|参考|文献|参照).*")
    
    regexRefStartPattern1 = re.compile("^\[.+.+$")
    regexRefStartPattern2 = re.compile("^\[\(|（][0-9]+[\)|）].+$")
    regexRefStartPattern3 = re.compile("^[0-9]+[\)|）|\.|　|\s].+$")

    for pageId, v in sorted(documentInfoOnPage.items(),reverse=True):
        pdfDocumentBlocks = v[0]
        pageInfo = v[1]        
        for i, pdfDocumentBlock in enumerate(pdfDocumentBlocks[::-1]):  
            #Exclude text that may be included in page headers and footers
            if isHeaderOrFooter(pageInfo.height, headerRatio, footerRatio, pdfDocumentBlock.y0, pdfDocumentBlock.y1):
                continue            
            if "Footnote" in pdfDocumentBlock.identifier:
                continue                          
            textLine = reduce(lambda x, y: x + y.text.replace("\n", ""), pdfDocumentBlock.pdfTextLines, "")
            #textLine = unicodedata.normalize('NFKC', textLine).lower()
            startHits =[
                re.search(regexRefStartPattern1, textLine.strip()),
                re.search(regexRefStartPattern2, textLine.strip()),
                re.search(regexRefStartPattern3, textLine.strip())        
            ]
            startHit = reduce(lambda x, y: x or y, startHits)                    
            if startHit:
                existStartPattern = True
            
            if re.search(regexTitlePattern, unicodedata.normalize('NFKC', textLine.strip()).lower()):
                existReferenceTitle = True
                referenceTitlePage = pageId
                break
        if existReferenceTitle:
            break    
    return existReferenceTitle, existStartPattern, referenceTitlePage


def getReference(documentInfoOnPage, headerRatio, footerRatio):
    """Get reference range text

    Args:
        documentInfoOnPage (_type_): _description_
        headerRatio (_type_): _description_
        footerRatio (_type_): _description_

    Returns:
        _type_: _description_
    """

    #Does it have a title that represents a reference? Is there a reference starting pattern?
    existReferenceTitle, existStartPattern, referenceTitlePage = haveReferenceTitle(documentInfoOnPage, headerRatio, footerRatio)
    if not existReferenceTitle and not existStartPattern:
        #In this case, reference cannot be obtained.
        return documentInfoOnPage

    if not existStartPattern:
        #In this case, basically you have no choice but to acquire in blocks.
        return getReferenceForExistStartPattern(documentInfoOnPage, headerRatio, footerRatio, referenceTitlePage)

    
    #regexRefStartPattern1 = re.compile("^\[.+\].+$")
    #When superscripts, subscripts, etc. are included, Sometimes the parentheses are broken and the closing parenthesis comes first.
    regexRefStartPattern1 = re.compile("^\[.+.+$")
    regexRefStartPattern2 = re.compile("^\[\(|（][0-9]+[\)|）].+$")
    regexRefStartPattern3 = re.compile("^[0-9]+[\)|）|\.|　|\s].+$")
    
    regexRefEnd = re.compile("\.$")

    #Care when a URL is added at the end of Reference text
    regexRefURLPattern = re.compile("(^.*\.)\s((http|https)\://.+$)")
    '''
    regexSpanOutPattern1 = re.compile("^(References|references|references|参考|文献|参照).*")
    regexSpanOutPattern2 = re.compile("^(\[1\]|\(1\)|（1）|1[\)|\[1）|\.|\s|　]).*")
    '''
    isRefSpan = False
    foundRefHead = False
    convertDocumentInfoOnPage  = {}
    isfinish = False
    isSpanOut = False

    sentences = []            
    sentence = ""
    existReferenceInLastPage = False
    prevFontSize = -1  
    lastPage  = max(documentInfoOnPage.keys()) 
    #Parsing from the end of the page
    for pageId, v in sorted(documentInfoOnPage.items(),reverse=True):
        pdfDocumentBlocks = v[0]
        pageInfo = v[1]        
        blockNoList = []
        if isfinish: #Reference analysis ends when the reference range is exceeded.
            convertDocumentInfoOnPage[pageId] = (pdfDocumentBlocks, pageInfo) 
        else:
            convertPdfDocumentBlocks = []                      
            for i, pdfDocumentBlock in enumerate(pdfDocumentBlocks[::-1]):  
                #Exclude text that may be included in page headers and footers
                if isHeaderOrFooter(pageInfo.height, headerRatio, footerRatio, pdfDocumentBlock.y0, pdfDocumentBlock.y1):
                    continue
                
                if "Footnote" in pdfDocumentBlock.identifier:
                    continue                

                sentence, blockNoList, fontSize, isReset, isSpanOut = getSentence(foundRefHead, pdfDocumentBlock, prevFontSize, sentence,blockNoList)
                if isReset: 
                    isRefSpan = False
                    sentences = []
                prevFontSize = fontSize

                endUrlHit = re.search(regexRefURLPattern, sentence)
                if endUrlHit and not sentence.endswith("."):
                    sentence += "."

                startHits =[
                    re.search(regexRefStartPattern1, sentence),
                    re.search(regexRefStartPattern2, sentence),
                    re.search(regexRefStartPattern3, sentence)        
                ]

                startHit = reduce(lambda x, y: x or y, startHits)                    
                endHit = re.search(regexRefEnd, sentence.strip())
                
                '''
                isSpanOuts =[
                    re.search(regexSpanOutPattern1, sentence),
                    re.search(regexSpanOutPattern2, sentence),        
                ]

                isSpanOut = reduce(lambda x, y: x or y, isSpanOuts)'
                '''
                if endHit:                       
                    isRefSpan = True
                else:
                    sentence = ""

                if isRefSpan:
                    blockNoList.append(i)     
                    if startHit:                        
                        foundRefHead = True    
                        if not sentence.strip() == "":
                            sentences.append(sentence)                        
                            sentence = ""
                
                if isRefSpan and isSpanOut:
                    break
                
                
            references = sentences[::-1]            
            if lastPage == pageId and len(references) > 0:
                existReferenceInLastPage = True

            isfinish = isSpanOut or not existReferenceInLastPage
            indices = list(map(lambda x: len(pdfDocumentBlocks)-x-1 ,blockNoList[::-1]))
            
            for i, pdfDocumentBlock in enumerate(pdfDocumentBlocks):
                if not i in indices or isHeadline(pdfDocumentBlock):
                    convertPdfDocumentBlocks.append(pdfDocumentBlock)                            

            pageInfo.references = copy.copy(references)
            sentences = []
            references = []
            indices = []
            blockNoList = []
            convertDocumentInfoOnPage[pageId] = (convertPdfDocumentBlocks, pageInfo)
            
        
    #Since the page ID is in descending order, change it back to ascending order.
    return dict((x, y) for x, y in sorted(convertDocumentInfoOnPage.items()))


def isHeadline(pdfDocumentBlock:PdfDocumentBlock):
    result = False
    regexTitlePattern = re.compile("^.*(references|参考|文献|参照).*")
    regexHeadlinePattern = re.compile("^(|\/\/Document\/H|\/\/Document\/Sect.*\/H)")
    text = unicodedata.normalize('NFKC', pdfDocumentBlock.pdfTextLines[0].text.strip()).lower()
    if re.search(regexTitlePattern, text):
        if re.search(regexHeadlinePattern, pdfDocumentBlock.identifier):
            result = True
    return result

def getReferenceForExistStartPattern(documentInfoOnPage, headerRatio, footerRatio, referenceTitlePage):
    """Reference acquisition in case there is no reference starting line pattern

    Args:
        documentInfoOnPage (_type_): _description_
        headerRatio (_type_): _description_
        footerRatio (_type_): _description_
        referenceTitlePage (_type_): _description_

    Returns:
        _type_: _description_
    """
    #If there is no reference line head pattern, it is basically acquired in blocks.
    isRefSpan = False
    regexTitlePattern = re.compile("^(References|references|references|参考|文献|参照).*")
    convertDocumentInfoOnPage = {}
    isFinish = False
    sentences = []            
    sentence = ""

    for pageId, v in documentInfoOnPage.items():
        pdfDocumentBlocks = v[0]
        pageInfo = v[1]                 
        if pageId < referenceTitlePage or isFinish:
            convertDocumentInfoOnPage[pageId] = v
        else:
            convertPdfDocumentBlocks = []
            for i, pdfDocumentBlock in enumerate(pdfDocumentBlocks):
                if isFinish :
                    convertPdfDocumentBlocks.append(pdfDocumentBlock)
                else:
                    textLine = reduce(lambda x, y: x + y.text.replace("\n", ""), pdfDocumentBlock.pdfTextLines, "")
                    if re.search(regexTitlePattern, textLine.strip()):
                        isRefSpan = True
                        continue
                    if isRefSpan:
                        #Reference analysis ends when the heading line appears.
                        if pdfDocumentBlock.identifier.startswith("//Document/H") or re.search("^\/\/Document/Sect.*\/H", pdfDocumentBlock.identifier):                        
                            isFinish = True
                        else:
                            sentence += textLine
                            isLabel = re.search("^\/\/Document/L.*\/Lbl", pdfDocumentBlock.identifier)
                            if not isLabel and textLine.strip().endswith("."):                            
                                sentences.append(sentence)
                                sentence = ""
                    else:
                        convertPdfDocumentBlocks.append(pdfDocumentBlock)  

            pageInfo.references = copy.copy(sentences)                    
            convertDocumentInfoOnPage[pageId] = (convertPdfDocumentBlocks, pageInfo)
            sentences = []

    return convertDocumentInfoOnPage
