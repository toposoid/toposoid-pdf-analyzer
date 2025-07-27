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

from .PdfExtractorCommon import calcDistance, isHeaderOrFooter, existLabel, getLabels, getLang, getParagraphSeparator, getSentenceSeparator, encodeSentence, decodeSentence, divideTextByLength, cleanLabelSpace, getDummyReplaceStrDict, SENTENCE_SEPARATOR_REGEX_UNKNOWN
from .PdfPreprocess import preprocess, preprocessForTest
import mojimoji
import re
import numpy as np
from functools import reduce
import os
import copy
import ToposoidCommon as tc
from ToposoidCommon.model import Reference, ImageReference, TableReference,  KnowledgeForImage, KnowledgeForTable, Knowledge, DocumentPageReference, KnowledgeForDocument
from .model import TextBlock, ParagraphInfo
from typing import List

LOG = tc.LogUtils(__name__)

def mergeDictForConstructingKnowledges(dict1, dict2):
    """Merging content with the same label

    Args:
        dict1 (_type_): 
        dict2 (_type_): 

    Returns:
        _type_: 
    """
    resultDict = dict1
    for k, v in dict2.items():
        if k  in resultDict:
           resultDict[k] += v 
        else:
           resultDict[k] = v 
    return resultDict

def linkContentAndTextByCoords(pdfDocumentBlocks, pageInfo, contentsInfo, mainFontSizeMin = 10, headerRatio=0.05, footerRatio=0.05):
    """Merge content to text coordinates

    Args:
        pdfDocumentBlocks (_type_): _description_
        pageInfo (_type_): _description_
        contentsInfo (_type_): _description_
        mainFontSizeMin (int, optional): _description_. Defaults to 10.
        headerRatio (float, optional): _description_. Defaults to 0.05.
        footerRatio (float, optional): _description_. Defaults to 0.05.

    Returns:
        _type_: _description_
    """
    #Extract only items without labels
    targetContents = list(filter(lambda x: x.label == "", contentsInfo))
    if len(targetContents) == 0:
        return {}

    linkedContentDict = {}
    for pdfContentsInfo in targetContents:
        coodinate = pdfContentsInfo.coodinate
        minDistance = np.inf
        bestMatchTextNo = -1 
        for i, pdfDocumentBlock in enumerate(pdfDocumentBlocks): 
            selectedPdfTextLines =  list(filter(lambda x: x.fontSize >= mainFontSizeMin, pdfDocumentBlock.pdfTextLines))             
            if len(selectedPdfTextLines) == 0:
                continue            
            #Exclude text that may be included in page headers and footers
            if isHeaderOrFooter(pageInfo.height, headerRatio, footerRatio, pdfDocumentBlock.y0, pdfDocumentBlock.y1):
                continue

            textPoint = (pdfDocumentBlock.x0, pdfDocumentBlock.y0)            
            d = calcDistance((coodinate.x0, coodinate.y0) , textPoint)
            if d < minDistance:
                minDistance = d
                bestMatchTextNo = i 

        if bestMatchTextNo in linkedContentDict:
            linkedContentDict[bestMatchTextNo].append(pdfContentsInfo)
        else:
            linkedContentDict[bestMatchTextNo] = [pdfContentsInfo]

    #For debug
    '''
    for k, v in linkedContentDict.items():
        print("-------------------------------------")
        selectedPdfTextLines =  list(filter(lambda x: x.fontSize >= mainFontSizeMin, pdfDocumentBlocks[k].pdfTextLines))      
        text = reduce(lambda x, y: x.text + y.text, selectedPdfTextLines)
        print(text)
        for imgInfo in v:
            print(imgInfo)
    '''
    return linkedContentDict

#この調整をしないとtextblocksの数を数え間違える。顕著な例は、ブロック文字列がパラグラフの先頭に付く
def addBlockString(x, blockBorder, sentenceSeparator, isLast):
    if isLast:
        return x
    else:        
        if sentenceSeparator == SENTENCE_SEPARATOR_REGEX_UNKNOWN:
            return x +  blockBorder
        if re.search(sentenceSeparator + "+?$", x):
            terminateSpace = ""
            hit = re.search("(\s+?)$", x) 
            if hit:
                terminateSpace = hit.group(1)
            return re.sub(sentenceSeparator + "+?$", blockBorder + "\g<1>" + terminateSpace , x)
        else:
            return x +  blockBorder


def adjustTextBlocks(textBlocks:List[TextBlock], ):
    shrinkingTextBox = []        
    isTarget = False             
    for textBlock in textBlocks:
        if textBlock.text == "~  ":
            isTarget =True                
        else:
            #連続したパラグラフ区切りは、一つにまとめる
            if isTarget:
                shrinkingTextBox.append(TextBlock(text= "~  " + textBlock.text, pageId=textBlock.pageId))
            else:
                shrinkingTextBox.append(textBlock)
            isTarget = False

    #最後がパラグラフ区切りの場合の処理
    #この場合は、区切り文字は後ろにつける
    #TODO:textBlocksの要素が一つのときは、この対応は意味がない。。。
    #if isTarget:
    #    shrinkingTextBox[-1] = TextBlock(text=shrinkingTextBox[-1].text + "~  ", pageId=textBlock.pageId)
    if isTarget:
        shrinkingTextBox.append(TextBlock(text="~  ", pageId=textBlock.pageId))        
    return shrinkingTextBox

def getDivideTextBlockIndex(paragraphRegex, paragraphSeparateCount, textBlocks):
    resultIndex = 0
    count = 0
    totalText = ""
    for i, textBlock in enumerate(textBlocks):
        #パラグラフ境界は、textBlocksの要素を繋げないとわからない
        totalText += textBlock.text
        if re.search(paragraphRegex, totalText):
             count += 1
             resultIndex = i        
        if count == paragraphSeparateCount:
            break                                          
    return resultIndex


def getParagraphs(textBlocks:List[TextBlock], forceAddParagraph:bool):
    paragraphs:List[ParagraphInfo] = []

    if len(textBlocks) == 0:
        return paragraphs, textBlocks
    
    #パラグラフ区切りではあるが、ヘッドラインとして避けているものの存在を想定
    onlyHeadlineLikeSeparatorTextBoxs = list(filter(lambda x: x.text == "~  ", textBlocks))
    if len(onlyHeadlineLikeSeparatorTextBoxs) > 0:
        if len(textBlocks) == 1:                    
            return paragraphs, textBlocks
        elif len(onlyHeadlineLikeSeparatorTextBoxs) == len(textBlocks):
            return paragraphs, textBlocks
        else:
            #この状況ではtextBlockの調整が可能。区切り文字を前後のどちらかに移動せさてtextBlocksをシュリンク            
            textBlocks = adjustTextBlocks(textBlocks)

    #パラグラフセパレータを取得する目的で一度BLOCK区切りなしで全体の文字列を取得する。
    lang = getLang("".join(list(map(lambda x: x.text, textBlocks))))
    sentenceSeparator = getSentenceSeparator(lang)
    paragraphRegex = getParagraphSeparator(lang)

    blockBorder = getDummyReplaceStrDict()[""]
     
    #TODO:ここを丁寧に処理する必要がある。
    totalText = "".join(list(map(lambda x:  addBlockString(x[1].text, blockBorder, sentenceSeparator, x[0]==len(textBlocks)-1), enumerate(textBlocks))))
    #totalText = reduce(lambda x, y: x.text + blockBorder + y.text, textBlocks)
        
    if not forceAddParagraph:
        #If you do not want to force paragraphs, check the sentence breaks and paragraph breaks.強制的にパラグラフ化しない場合は、文章区切り、パラグラフ区切りのチェックを行う        
        if not re.search(paragraphRegex, totalText):
            return paragraphs, textBlocks
        
    #totalText = encodeSentence(totalText, sentenceSeparator) 
    totalText = encodeSentence(totalText, sentenceSeparator)

    if re.search(paragraphRegex, totalText):    
        paragraphSeparateCount = 0                            
        confirmedParagraphs = re.split(paragraphRegex, totalText)        
        paragraphText = ""
        for j, paragraph in enumerate(confirmedParagraphs):
            if paragraph is None:
                continue
            if j == len(confirmedParagraphs) - 1:
                #The last element is not determined.
                if paragraph.strip() == "":
                    #totalText = "" 
                    textBlocks = []
                else:
                    if forceAddParagraph:
                        #If there is a paragraph that does not span pages and has not yet been determined, the paragraph is determined regardless of whether there is a break or not.                        
                        idx = len(paragraphText.split(blockBorder))
                        textBlocksInParagraph = copy.copy(textBlocks[:idx])
                        textBlocks =  textBlocks[idx:]                                          
                        paragraphs.append(ParagraphInfo(totalText=paragraph, textBlocks=textBlocksInParagraph))
                        #totalText = ""
                    #else:
                    #    textBlocks = ?
                    #    #totalText = paragraph                        
            else:
                #If a regular expression has a group, the split function in the re library will include the delimiter in the list.
                if re.search(paragraphRegex, paragraph): 
                    #TODO:下記ケアが必要か今一度チェック
                    #Paragraph boundaries have one more space than sentence breaks, so drop one space.                     
                    fixedParagrah = paragraphText + paragraph
                    paragraphSeparateCount += 1                    
                    idx = getDivideTextBlockIndex(paragraphRegex, paragraphSeparateCount, textBlocks)
                    

                    #TODO:パラグラフ境界でTextBlockを分割する必要がある。
                    currentBlock = textBlocks[idx]                    
                    previousBlocks = textBlocks[:idx] 
                    previousBlocksText = reduce(lambda x, y: x + y.text, previousBlocks, "")
                    previousBlocksText = encodeSentence(previousBlocksText, sentenceSeparator) 
                    currentText = fixedParagrah.replace(blockBorder, "").replace(previousBlocksText, "")

                    textBlocksInParagraph =  previousBlocks + [TextBlock(text=currentText, pageId = currentBlock.pageId)]                    
                    paragraphs.append(ParagraphInfo(totalText=fixedParagrah, textBlocks=textBlocksInParagraph))
                    
                    #-------------
                    tempText = reduce(lambda x, y: x + y.text, textBlocks[:idx+1], "")                    
                    tempText = encodeSentence(tempText, sentenceSeparator)                     
                    #tempText =  blockBorder.join(list(map(lambda x: x.text, textBlocks[:idx]))) 
                    secondTextBlocks = []
                    residual = tempText[len(encodeSentence(fixedParagrah.replace(blockBorder, ""), sentenceSeparator)):]
                    if not residual == "": #Block境界とパラグラフ境界ば同じでない場合（こちらが通常のケース）                        
                        #この状況では、先頭に~  があった場合は、パラグラフとして区切ったことになるのでその後に残さない
                        secondTextBlocks = [TextBlock(text= re.sub("^~\s\s", "", residual), pageId = currentBlock.pageId)] 
                    else:
                        #residualがない場合でも先頭要素に先頭に~  があった場合は、パラグラフとして区切ったことになるのでその後に残さない
                        if len(textBlocks[idx + 1:]) > 0:
                            textBlocks[idx + 1] = TextBlock(text= re.sub("^~\s\s", "", textBlocks[idx + 1].text), pageId = textBlocks[idx +1].pageId)
                    
                    textBlocks = secondTextBlocks + textBlocks[idx+1 :]                        
                    paragraphText = ""              
                else:
                    paragraphText += paragraph
                
    else:
        if forceAddParagraph:
            #If there is a paragraph that does not have a paragraph boundary and has not yet been determined, the paragraph is determined regardless of whether there is a break or not.
            paragraphs.append(ParagraphInfo(totalText=totalText, textBlocks=textBlocks))
            textBlocks = [] 


    return paragraphs, textBlocks

def extractParagraph(documentInfoOnPage, isPageDivisionTarget, headerRatio=0.05, footerRatio=0.05):        
    """Paragraph extraction

    Args:
        documentInfoOnPage (_type_): 
        isPageDivisionTarget (bool): 
        headerRatio (float, optional): _description_. Defaults to 0.05.
        footerRatio (float, optional): _description_. Defaults to 0.05.

    Returns:
        _type_: 
    """
    paragraphs:List[ParagraphInfo] = []
    textBlocks:List[TextBlock] = []
    pageId = 1
    prevPageId = 1
    blockBorder = getDummyReplaceStrDict()[""]
    for v in documentInfoOnPage.values():
        pdfDocumentBlocks = v[0]    
        pageInfo = v[1]    
        
        for i, pdfDocumentBlock in enumerate(pdfDocumentBlocks):
            excludeTextLines = list(filter(lambda z: z.fontSize < pageInfo.mainFontSize, pdfDocumentBlock.pdfTextLines))            
            #Determine if all font sizes are less than the main font size and decide whether to import it as text
            if len(excludeTextLines) == len(pdfDocumentBlock.pdfTextLines):
                continue   

            #Exclude text that may be included in page headers and footers
            if isHeaderOrFooter(pageInfo.height, headerRatio, footerRatio, pdfDocumentBlock.y0, pdfDocumentBlock.y1):
                continue
        
            pageId = pdfDocumentBlock.pageId            
            text = reduce(lambda x, y: x + y.text, pdfDocumentBlock.pdfTextLines, "") 
            if text == "":
                continue
            textBlock = TextBlock(text=text, pageId=pdfDocumentBlock.pageId)

            if isPageDivisionTarget:
                if pageId == prevPageId:
                    textBlocks.append(textBlock)
                else:
                    totalText = blockBorder.join(list(map(lambda x: x.text, textBlocks)))                    
                    lang = getLang(totalText)
                    sentenceSeparator = getSentenceSeparator(lang)
                    blockBorder = getDummyReplaceStrDict()[""]                    
                    paragraphInfo = ParagraphInfo(totalText=encodeSentence(totalText, sentenceSeparator), textBlocks=copy.copy(textBlocks))                
                    paragraphs.append(paragraphInfo)
                    textBlocks = []
                    textBlocks.append(textBlock)
            else:
                if pdfDocumentBlock.identifier == pageInfo.pageBreakIdentifier:
                    #page break
                    textBlocks.append(textBlock)
                    break                                                         
                else:
                    textBlocks.append(textBlock)
                    additionalParagraph, textBlocks = getParagraphs(textBlocks, False) 
                    if len(additionalParagraph) > 0:
                        paragraphs += copy.copy(additionalParagraph)
                        additionalParagraph = []
            
            #I want to update it every time, so the update location is here
            prevPageId = pageId

        #lastTextBlocks = textBlocks
        prevPageId = pageId

    
    if len(textBlocks) > 0:
        if isPageDivisionTarget:
            totalText = blockBorder.join(list(map(lambda x: x.text, textBlocks)))
            lang = getLang(totalText)
            sentenceSeparator = getSentenceSeparator(lang)
            blockBorder = getDummyReplaceStrDict()[""]              
            paragraphInfo = ParagraphInfo(totalText=encodeSentence(totalText, sentenceSeparator), textBlocks=textBlocks)                
            paragraphs.append(paragraphInfo)            
        else:
            additionalParagraph, textBlocks = getParagraphs(textBlocks, True)        
            if len(additionalParagraph) > 0:
                paragraphs += copy.copy(additionalParagraph)
                additionalParagraph = []

    #TODO:テスト用
    #for paragraph in paragraphs:        
    #    print(paragraph.totalText)        
    #    print("------------------------------------------------------------------\n")
    return list(filter(lambda x: x.totalText != "~  " and x.totalText != "", paragraphs))



def makeKnowledgeForNoRefference(documentId, filename, linkedContentDict, contentLabelDict, hitLabels, lang, pageInfoDict, appearedPageIds):
    """For Contents without labels

    Args:
        documentId (_type_): _description_
        linkedContentDict (_type_): _description_
        contentLabelDict (_type_): _description_
        hitLabels (_type_): _description_
        lang (_type_): _description_
        pageInfoDict (_type_): _description_
        appearedPageIds (_type_): _description_

    Returns:
        _type_: _description_
    """
    noRefferenceContents = list(linkedContentDict.values())
    #A group of content that has a label but is not referenced anywhere.　
    #Content that requires a key in contentLabelDict and that key does not exist in hitLabels    
    noRefferenceContents += list(map(lambda y: y[1],list(filter(lambda x: not x[0] in hitLabels, contentLabelDict.items()))))
    
    knowledgeForImageDict = {}
    knowledgeForTableDict = {}
    usedUrls = []
    pageIds = []
    knowledgeForDocument = getKnowledgeForDocument(documentId, filename, pageInfoDict)

    #Summarize with the text NO-REFFERENCE_DocumentId_PageNo.
    for contentList in noRefferenceContents:
        for pdfContentFileInfo in contentList:            
            url = os.environ["TOPOSOID_CONTENTS_URL"] +  re.sub("^contents/", "", pdfContentFileInfo.path)
            if not url in usedUrls:
                usedUrls.append(url)
                pageId = pdfContentFileInfo.page.pageId
                pageIds.append(pageId)
                ref = Reference(url=url, surface="", surfaceIndex=-1,isWholeSentence=True, originalUrlOrReference=url, metaInformations=pdfContentFileInfo.metaList)
                if pdfContentFileInfo.contentType.startswith("IMAGE"):
                    imgWidth= int(pdfContentFileInfo.coodinate.x1) - int(pdfContentFileInfo.coodinate.x0)
                    imgHeight= int(pdfContentFileInfo.coodinate.y1) - int(pdfContentFileInfo.coodinate.y0)
                    imgRef = ImageReference(reference=ref, x=0, y=0, width=imgWidth, height=imgHeight)                    
                    if pageId in knowledgeForImageDict:
                        knowledgeForImageDict[pageId].append(KnowledgeForImage(id=pdfContentFileInfo.id, imageReference=imgRef))
                    else:
                        knowledgeForImageDict[pageId] = [KnowledgeForImage(id=pdfContentFileInfo.id, imageReference=imgRef)]                    
                elif pdfContentFileInfo.contentType.startswith("TABLE"):
                    tableRef = TableReference(reference=ref)
                    if pageId in knowledgeForTableDict:
                        knowledgeForTableDict[pageId].append(KnowledgeForTable(id=pdfContentFileInfo.id, tableReference=tableRef))
                    else:
                        knowledgeForTableDict[pageId] = [KnowledgeForTable(id=pdfContentFileInfo.id, tableReference=tableRef)]
    knowledges = []

    for pageId, pageInfo in pageInfoDict.items():
        isNonSentenceOnly = not pageId in appearedPageIds #Table of contents only or reference only page
        knowledgeForImages = []
        knowledgeForTables = []

        if pageId in pageIds :
            if pageId in knowledgeForImageDict:
                knowledgeForImages = knowledgeForImageDict[pageId]
            if pageId in knowledgeForTableDict:
                knowledgeForTables = knowledgeForTableDict[pageId]
        
        if len(knowledgeForImages) > 0 or len(knowledgeForTables) > 0 or (len(pageInfo.references) > 0 and isNonSentenceOnly) or (len(pageInfo.tableOfContents) > 0 and isNonSentenceOnly) or (len(pageInfo.headlines) > 0 and isNonSentenceOnly):
            documentPageReference = DocumentPageReference(pageNo=pageId, references=pageInfo.references, tableOfContents=pageInfo.tableOfContents, headlines = pageInfo.headlines, titleOfTopPage=pageInfo.titleOfTopPage)
            knowledges.append(Knowledge(sentence="NO_REFERENCE_" + documentId + "_" + str(pageId), lang="@@_#1", extentInfoJson="{}",isNegativeSentence=False,knowledgeForImages=knowledgeForImages,knowledgeForTables=knowledgeForTables, knowledgeForDocument = knowledgeForDocument, documentPageReference=documentPageReference))

    return knowledges


def getKnowledgeForDocument(documentId, filename, pageInfoDict):
    titleOfTopPage = ""
    for pageInfo in pageInfoDict.values():
        if not pageInfo.titleOfTopPage == "":
            titleOfTopPage = pageInfo.titleOfTopPage
            break
    url = os.environ["TOPOSOID_CONTENTS_URL"] +  f"documents/{documentId}.pdf"
    return KnowledgeForDocument(id=documentId, filename=filename, url=url, titleOfTopPage=titleOfTopPage)

def getTextElements(paragraphInfo:ParagraphInfo, sentenceSeparator, lang, deepDivideFlag):
    
    #まずsentenceSeparatorで区切る    
    if not re.search(sentenceSeparator, paragraphInfo.totalText):
        textElements = [(paragraphInfo.totalText, paragraphInfo.textBlocks[0].pageId)]
    else:
        textElements = re.split(sentenceSeparator, paragraphInfo.totalText)
        textElementsWithPage = []
        blockBorder = getDummyReplaceStrDict()[""]
        currentBlock = 0
        for textElement in textElements:
            if currentBlock < len(paragraphInfo.textBlocks):
                pageId = paragraphInfo.textBlocks[currentBlock].pageId          
            
            currentBlock += textElement.count(blockBorder)
            textElementsWithPage.append((textElement, pageId))

        #Restores the period that appears in the middle of the replaced sentence.
        textElements = list(map(lambda x: (decodeSentence(x[0]), x[1]) , textElementsWithPage))
        textElements = divideTextByLength(textElements, sentenceSeparator, lang, deepDivideFlag)
        
    return textElements



def makeKnowledges(documentId, filename, paragraphs, linkedContentDict, contentLabelDict, pageInfoDict, deepDivideFlag, isPageDivisionTarget):
    """Create a list of Knowledge objects from paragraph information

    Args:
        documentId (_type_): _description_
        paragraphs (_type_): _description_
        linkedContentDict (_type_): _description_
        contentLabelDict (_type_): _description_
        pageInfoDict (_type_): _description_
        deepDivideFlag (_type_): _description_
        isPageDivisionTarget (bool): _description_

    Returns:
        _type_: _description_
    """
    propositions = []
    knowledges = []
    contentLabels = contentLabelDict.keys()
    hitLabels = []
    usedUrls = []
    sentence = ""
    convertSentence = ""
    lang = ""
    langAsDocument = ""    
    
    knowledgeForDocument = getKnowledgeForDocument(documentId, filename, pageInfoDict)

    #Divide the sentence into periods.
    for paragraphInfo in paragraphs:
        
        #For each paragraph, determine whether it is English or Japanese and determine the separator.
        lang = getLang(paragraphInfo.totalText)
        sentenceSeparator = getSentenceSeparator(lang)
        
        langAsDocument = lang
        
        #Is there a period or not? When splitting with a period, it is not possible to distinguish between one period and no period.
        existSeparator = False
        haveTerminateSeparator = False
        if re.search(sentenceSeparator, paragraphInfo.totalText): 
            existSeparator = True  
        #Is the first and last character the end of a period?
        if re.search(sentenceSeparator + "$", paragraphInfo.totalText):
            haveTerminateSeparator = True

        textElements = getTextElements(paragraphInfo, sentenceSeparator, lang, deepDivideFlag)

        '''
        if not re.search(sentenceSeparator, paragraphInfo.totalText) and not isPageDivisionTarget:
            textElements = [paragraphInfo.totalText]
        else:
            textElements = list(filter(lambda x: (x is not None) and (not x.strip() == ''), re.split(sentenceSeparator, paragraphInfo.totalText)))
            if len(textElements) == 0:
                continue
            
            #Restores the period that appears in the middle of the replaced sentence.
            textElements = list(map(lambda x: decodeSentence(x) , textElements))
            #TODO:divideする時にBlockで区切れるように調整したい。区切ったとしても大きくなる文字列はどうすりゃいいのか？
            textElements = divideTextByLength(textElements, sentenceSeparator, lang, deepDivideFlag)
        '''
        knowledgeForImages = []
        knowledgeForTables = []

        #Binding content with labels to text
        for i, textElementWithPage in enumerate(textElements): 
            textElement =  textElementWithPage[0]
            pageId = textElementWithPage[1]

            documentPageReference = DocumentPageReference(pageNo=pageId, references=pageInfoDict[pageId].references, tableOfContents=pageInfoDict[pageId].tableOfContents, headlines=pageInfoDict[pageId].headlines)
            sentence += textElement
            convertSentence += mojimoji.zen_to_han(textElement.strip(), kana=False).lower()                        
            if existLabel(convertSentence, False):
                for label in getLabels(convertSentence, False):                    
                    if label in contentLabels:
                        hitLabels.append(label)
                        #Considering that multiple files may be linked
                        for pdfContentFileInfo in contentLabelDict[label]:
                            url = os.environ["TOPOSOID_CONTENTS_URL"] +  re.sub("^contents/", "", pdfContentFileInfo.path)
                            if not url in usedUrls:
                                usedUrls.append(url)
                                ref = Reference(url=url, surface=label, surfaceIndex=-1,isWholeSentence=False, originalUrlOrReference=url, metaInformations=pdfContentFileInfo.metaList)
                                if pdfContentFileInfo.contentType.startswith("IMAGE"):
                                    imgWidth= int(pdfContentFileInfo.coodinate.x1) - int(pdfContentFileInfo.coodinate.x0)
                                    imgHeight= int(pdfContentFileInfo.coodinate.y1) - int(pdfContentFileInfo.coodinate.y0)
                                    imgRef = ImageReference(reference=ref, x=0, y=0, width=imgWidth, height=imgHeight)
                                    knowledgeForImages.append(KnowledgeForImage(id=pdfContentFileInfo.id, imageReference=imgRef))
                                elif pdfContentFileInfo.contentType.startswith("TABLE"):
                                    tableRef = TableReference(reference=ref)
                                    knowledgeForTables.append(KnowledgeForTable(id=pdfContentFileInfo.id, tableReference=tableRef))

            isOnlyPeriod = re.search("^" + sentenceSeparator.replace("\s", "") + "$" , sentence)
            if isOnlyPeriod:
                #Delete the tilde that was arbitrarily inserted as a sentence break
                if sentence == "~":
                    sentence = ""
            else:
                #TODO: If there is a tilde at the beginning or end of the line in the original sentence, it will be removed, but that is a problem.
                sentence = re.sub("~$", "", sentence)
                sentence = re.sub("^~", "", sentence)
                #Register unless what remains after deleting the tilde is a period.

            #Remove spaces in labels. This will cause problems in matching with the results of predicate structure analysis later.
            sentence = cleanLabelSpace(sentence).strip()
            if sentence == "":
                continue
            if isPageDivisionTarget:
                #In the case of pagination, knowledge is formed by page-based paragraphs.
                if not isOnlyPeriod:
                    knowledge = Knowledge(sentence=sentence, lang=lang, extentInfoJson="{}",isNegativeSentence=False,knowledgeForImages=knowledgeForImages,knowledgeForTables=knowledgeForTables, knowledgeForDocument=knowledgeForDocument, documentPageReference=documentPageReference)
                    knowledges.append(knowledge)
                    convertSentence = ""
                    sentence = ""
                    knowledgeForImages = []
                    knowledgeForTables = []
                    usedUrls = []
            else:
                if existSeparator:
                    hit = re.search(sentenceSeparator.replace("\s", ""), textElement)                
                    if hit and not isOnlyPeriod:
                        #separator = hit.group(1)
                        if i < len(textElements) - 1:                                                    
                            knowledge = Knowledge(sentence=sentence, lang=lang, extentInfoJson="{}",isNegativeSentence=False,knowledgeForImages=knowledgeForImages,knowledgeForTables=knowledgeForTables, knowledgeForDocument=knowledgeForDocument, documentPageReference=documentPageReference)
                            knowledges.append(knowledge)
                            convertSentence = ""
                            sentence = ""
                            knowledgeForImages = []
                            knowledgeForTables = []
                            usedUrls = []
                        else:
                            if haveTerminateSeparator or isPageDivisionTarget:                                    
                                knowledge = Knowledge(sentence=sentence, lang=lang, extentInfoJson="{}",isNegativeSentence=False,knowledgeForImages=knowledgeForImages,knowledgeForTables=knowledgeForTables, knowledgeForDocument=knowledgeForDocument, documentPageReference=documentPageReference)
                                knowledges.append(knowledge)
                                convertSentence = ""
                                sentence = ""
                                knowledgeForImages = []
                                knowledgeForTables = []
                                usedUrls = []
            
        propositions.append(knowledges)
        knowledges = []


    #Care of table of contents, References, etc. 
    #If the entire page is a reference or table of contents, pageInfoDict information cannot be linked to Knowledge.    .
    #Organize information on linked pages
    appearedPageIds = []
    for knowledges in propositions:        
        appearedPageIds += list(map(lambda x: x.documentPageReference.pageNo, knowledges))
    appearedPageIds = set(appearedPageIds)

    noRefferenceKnowledges = makeKnowledgeForNoRefference(documentId, filename, linkedContentDict, contentLabelDict, hitLabels, langAsDocument, pageInfoDict, appearedPageIds)
    if not noRefferenceKnowledges is None:
        propositions.append(noRefferenceKnowledges)

    return list(filter(lambda x: len(x) > 0,  propositions))

def constructLabelDict(contentList):
    """Create a dictionary of labelsCreate a dictionary using image and table data labels as keys

    Args:
        contentList (_type_): _description_

    Returns:
        _type_: _description_
    """
    resultDict = {}
    for content in contentList:
        if content.label in resultDict:
            resultDict[content.label].append(content)
        else:
            resultDict[content.label] = [content]
    return resultDict

def mergePdfContents(documentId, filename, transversalState, headerRatio=0.05, footerRatio=0.05, deepDivideFlag=False, isTest=False):
    """Create a list of propositions by merging text, images, table data, and label information

    Args:
        documentId (_type_): _description_
        filename (_type_): _description_
        transversalState (_type_): _description_
        headerRatio (float, optional): _description_. Defaults to 0.05.
        footerRatio (float, optional): _description_. Defaults to 0.05.
        deepDivideFlag (bool, optional): _description_. Defaults to False.
        isTest (bool, optional): _description_. Defaults to False.

    Returns:
        _type_: _description_
    """
    if isTest:
        documentInfoOnPage, images, tables, isPageDivisionTarget = preprocessForTest(documentId, headerRatio, footerRatio, transversalState)        
    else:
        documentInfoOnPage, images, tables, isPageDivisionTarget = preprocess(documentId, filename, headerRatio, footerRatio, transversalState)

    #Label extraction
    contentLabelDict = {}
    imageLabelDict = constructLabelDict(images)
    tabelLabelDict = constructLabelDict(tables)
    contentLabelDict = mergeDictForConstructingKnowledges(contentLabelDict, imageLabelDict)
    contentLabelDict = mergeDictForConstructingKnowledges(contentLabelDict, tabelLabelDict)

    #Font size statistics extraction
    #TODO: Is it better to make it also obtainable from environment variables?
    fontSizeList = []
    for pdfDocumentBlocks in list(map(lambda x: x[0],  documentInfoOnPage.values())):
        textLines = list(map(lambda x : x.pdfTextLines, pdfDocumentBlocks))
        for textLine in list(reduce(lambda x, y: x + y, textLines, [])):
            for i in range(len(textLine.text)):
                fontSizeList.append(textLine.fontSize)        
    fontSizeList.sort(reverse=True)
    fontSizes, freq = np.unique(fontSizeList, return_counts=True)
    mainFontSizeMin = min(fontSizes[freq == np.amax(freq)]) 

    paragraphs = extractParagraph(documentInfoOnPage, isPageDivisionTarget, headerRatio=headerRatio, footerRatio=footerRatio)

    linkedContentDict = {} 
    pageInfoDict = {}   
    for pageId, v in documentInfoOnPage.items():
        pdfDocumentBlocks = v[0]
        pageInfo = v[1]
        imagesInfo = list(filter(lambda x: x.page.pageId == pageId, images))
        tablesInfo = list(filter(lambda x: x.page.pageId == pageId, tables))
        linkedImageDict = linkContentAndTextByCoords(pdfDocumentBlocks, pageInfo, imagesInfo, mainFontSizeMin, headerRatio=headerRatio, footerRatio=footerRatio)
        linkedTableDict = linkContentAndTextByCoords(pdfDocumentBlocks, pageInfo, tablesInfo, mainFontSizeMin, headerRatio=headerRatio, footerRatio=footerRatio)
        linkedContentDict = mergeDictForConstructingKnowledges(linkedContentDict, linkedImageDict)
        linkedContentDict = mergeDictForConstructingKnowledges(linkedContentDict, linkedTableDict)
        pageInfoDict[pageId] = pageInfo
    
    propositions = makeKnowledges(documentId, filename, paragraphs, linkedContentDict, contentLabelDict, pageInfoDict, deepDivideFlag, isPageDivisionTarget)
    #For Debug   
    '''
    for knowledges in propositions:        
        print("#####################################################################################################################")
        for i, knowledge in enumerate(knowledges):
            print("--------------------------------------------------------------------------------------------------------------")
            print(i)
            print(knowledge.sentence)
            for knowledgeForImage in knowledge.knowledgeForImages:
                ref = knowledgeForImage.imageReference.reference
                print(ref.surface, ref.isWholeSentence, ref.url, ref.metaInformations)        
            for knowledgeForTable in knowledge.knowledgeForTables:
                ref = knowledgeForTable.tableReference.reference
                print(ref.surface, ref.isWholeSentence, ref.url, ref.metaInformations)
    '''
    return propositions

