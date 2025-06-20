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
import numpy as np
from PIL import Image
import mojimoji
import pandas as pd
import regex
import math
import unicodedata
from ToposoidCommon.model import DetectedLanguage
import ToposoidCommon as tc

#LABEL_REGEX = re.compile(r"^((fig|figure|table|scheme|図|表)+[\.\- 　]*[0-9]+)(.*)")
#LABEL_REGEX_IN_SENTENCE = re.compile(r"((fig|figure|table|scheme|図|表)+[\.\- 　]*[0-9]+)(.*)")

LABEL_REGEX = re.compile(r"^((fig|figure|image|table|scheme|図|表|画像)+[\.\- 　]*[0-9]+)")
LABEL_REGEX_IN_SENTENCE = re.compile(r"((fig|figure|image|table|scheme|図|表|画像)+[\.\- 　]*[0-9]+)")

URL_LINK_REGEX = re.compile(r"(\(\<http.+?\>\))")

NUMBER_SYMBOL_REGEX = re.compile('^[0-9]+$')
ALPHABET_NUMBER_SYMBOL_REGEX = re.compile(r'^[ -~]*$')

JAPANNESE_REGEX = regex.compile(r"^.*([ぁ-ん]|[\u30A1-\u30F4]|\p{sc=Han}).*$")
ALPHABET_REGEX = re.compile(r"^.*[a-zA-Z]+.*$")

PARAGRAPH_SEPARATOR_REGEX_JP = r"([。\.~]\s\s)"
PARAGRAPH_SEPARATOR_REGEX_EN = r"([\.~\?!]\s\s)"
PARAGRAPH_SEPARATOR_REGEX_UNKNOWN = r"0^" #Regular expressions that match nothing

DUMMY_REPLACE_STR_DICT = {
    "。": "_#PERIOD_JP#_",
    ".": "_#PERIOD#_",
    "?": "_#QUESTIONMARK#_",
    "!": "_#EXCLAMATIONMARK#_",
    "~": "_#TILDE#_",
    "": "_#BLOCK#_"
}

SENTENCE_SEPARATOR_REGEX_JP = r"([。\.~])\s"
SENTENCE_SEPARATOR_REGEX_EN = r"([\.\?!~])\s"
SENTENCE_SEPARATOR_REGEX_UNKNOWN = r"0^" #Regular expressions that match nothing

LANG_JP="ja_JP"
LANG_EN="en_US"
LANG_UNKNOWN=""

MAX_CHARACTER_NUM_JP = 300
MIN_CHARACTER_NUM = 5

PROTECT_PERIOD_INDEX_REGEX = r"([0-9]+|\([0-9]+?\)|^[0-9]+\)|[①②③④⑤⑥⑦⑧⑨⑩]|[Ⅰ-Ⅹ]+|[\u2160-\u217F]+|[IXV]+|[ixv]+|^[a-rA-R]|\s[a-rA-R]|\([a-rA-R]\)|\s[a-rA-R]\)|(Fig|FIG|fig)|((etc|ex|cf|e\.g|i\.e|s\.t|et\sal|et\sseq|U\.S|U\.S\.A|U\.K|u\.s|u\.s\.a|u\.k)))\.\s"
#Since (s) and the like are often used as units, the alphabetical index will be limited to r.
DVIDED_BY_NO_PERIOD_REGEX = r"(\([0-9]+?\)|\s[0-9]+?\)|\([\u2160-\u217F]+?\)|\s[\u2160-\u217F]+?\)|\([IXV]+?\)|\s[IXV]+?\)|\([ixv]+?\)|\s[ixv]+?\)|\([a-rA-R]\)|\s[a-rA-R]\)|\s•\s|\s-\s|\s[①②③④⑤⑥⑦⑧⑨⑩]\s)"

'''
explicits = (
    u'\u202a', # LEFT-TO-RIGHT EMBEDDING
    u'\u202b', # RIGHT-TO-LEFT EMBEDDING
    u'\u202d', # LEFT-TO-RIGHT OVERRIDE
    u'\u202e', # RIGHT-TO-LEFT OVERRIDE
)
pdf = u'\u202c' # POP DIRECTIONAL FORMATTING
'''
def cleanExtraUnicode(s):
    """Excluding ExtraUnicode
    """
    targets = ["\u202a", "\u202b", "\u202d", "\u202e", "\u202c"]
    for target in targets:
        s = s.replace(target, "")
    return s

def getDummyReplaceStrDict():
    return DUMMY_REPLACE_STR_DICT


def cleanPdfUrlLink(s):
    """Excluding specific link expressions
    """
    result_iter = URL_LINK_REGEX.finditer(s)
    for result  in result_iter:
        s = s.replace(result.group(1), "")

    return s.replace("(<>)", "") #n-page links will look like (<>), so delete those too.

def cleanLabelSpace(s):
    result_iter = LABEL_REGEX_IN_SENTENCE.finditer(s)
    for result  in result_iter:
        s = s.replace(result.group(1), result.group(1).replace(" ", ""))
    return s

def getProtectPeriodIndexRegex():
    """Returns a regular expression for the period that should be protected, used for index etc.
    """
    return PROTECT_PERIOD_INDEX_REGEX

def preprocessText(text):
    """String normalization etc.
    """
    convertText = cleanExtraUnicode(text)
    convertText = convertText.replace("\n", "") #Remove a line break.  
    convertText = mojimoji.zen_to_han(convertText, kana=False) #Make everything half-width except kana.    
    convertText = cleanPdfUrlLink(convertText) #Remove pdf link
    #The reason why we don't separate English and Japanese is because there are rare sentences in Japanese that don't use punctuation marks and end with a period.
    '''
    ref. https://detail.chiebukuro.yahoo.co.jp/qa/question_detail/q12146518482
    日本語入力ソフトの仕様ではありません（多くの日本語入力ソフトは、「、。」を使うか「，．」を使うか設定で決めることはできますが）。印刷物のトレンドの変化に対応した、日本人の句読点利用の変化です。
    近年、出版業界では、縦書きの書籍は「、」と「。」、横書きの書籍は「，」と「．」として使い分けているところが増えました。とりわけ学術書はピリオドを句点、カンマを読点に使うことも多くなっています。学会誌の投稿規定に、句読点の使い方を定めていることもあります。「．」「，」を使うのは、「。」と「、」をベースにした句読点の体系は縦書きを対象に作られたものだからです。
    個人の書く文章も、そうしたトレンドと無関係ではなく、とりわけ縦書き・手書きでよりも、横書き・パソコン入力が一般的になった今日では、横書き印刷物に使われているピリオドを採用する人も増えている、ということでしょう。
    '''
      
    lang = getLang(convertText)
    sentenceSeparator = getSentenceSeparator(lang)
    #Consecutive half-width spaces following a sentence delimiter within a block are converted to a single space.
    if not sentenceSeparator == SENTENCE_SEPARATOR_REGEX_UNKNOWN:
        convertText = re.sub(sentenceSeparator + "+", "\g<1> ", convertText)

    return convertText

def addPeriodWithProtectSpecificPeriod(sentence, separator):
    """While protecting periods other than at the end of sentences, force sentence break + space. 

    Args:
        sentence (_type_): 
        separator (_type_): 

    Returns:
        _type_: sentence string
    """
    #First, protect periods that are not sentence breaks.
    convertSentence = re.sub(PROTECT_PERIOD_INDEX_REGEX, "\g<1>" + DUMMY_REPLACE_STR_DICT["."] + " ", sentence)
    #Protects emails, URLs, decimal points, etc.
    PROTECT_PERIOD_GENERAL_REGEX = r"([a-zA-Z]\.[a-zA-Z]|[0-9]\.[0-9]|\.[」\)\]\}])"
    convertSentence2 = ""
    for s in re.split(PROTECT_PERIOD_GENERAL_REGEX, convertSentence):
        if s is None or s.strip() == '':
            continue
        if re.search(PROTECT_PERIOD_GENERAL_REGEX, s):
            convertSentence2 += s.replace(".", DUMMY_REPLACE_STR_DICT["."])
        else:
            convertSentence2 += s
    #Force sentence break + space
    convertSentence2 = re.sub(separator.replace("\s", ""), "\g<1> ", convertSentence2)
    return convertSentence2
    
def forcePeriodSpaceSequence(textLine, isLongProposition, separator, lang):
    """Force sentence break + space.

    Args:
        textLine (_type_): 
        isLongProposition (bool): 
        separator (_type_): 
        lang (_type_): 

    Returns:
        _type_: 
    """

    #Protect the tilde because it is used as a sentence delimiter. This is done after obtaining the reference and table of contents, so it must be done at this location.
    textLine = textLine.replace("~", DUMMY_REPLACE_STR_DICT["~"])

    if lang == LANG_UNKNOWN or separator == SENTENCE_SEPARATOR_REGEX_UNKNOWN:
        return textLine
    
    #In most cases, there is no space after a period (.) in Japanese, so we take care of paragraph indentation in Japanese sentences.
    #However, if there is a paragraph, it becomes a period + space. In this case, we want to separate them into paragraphs, so special processing is applied.
    if not isLongProposition and lang == LANG_JP:      
          
        textLine = textLine.replace("。 ", "。  ") #Regarding the Japanese ".", we are forced to take care of the period and indentation. Paragraphs are separated by periods + 2 spaces.
        
    #Take care of periods with no spaces at the end of sentences
    textLine = re.sub(separator.replace("\s", "") + "$", "\g<1> ", textLine)

    #In the processing up to this point, the periods in the sentences within the block have not been converted to periods + spaces. 
    #In the case of Japanese punctuation marks, be sure to follow the format of punctuation + space.
    #In English, it is usually a period space, so we don't care about it. Conversely, a period may be included in proper nouns. If you force yourself to take care of this, you'll end up with strange divisions.        
    convertSentence = ""
    if lang == "ja_JP":
        for i, sentence in enumerate(re.split(separator, textLine)):   
            if sentence is None:
                continue             
            hit = re.search("^" + separator.replace("\s", "") + "$", sentence)
            if hit:
                #Additional information due to lack of space.
                convertSentence += hit.group(1) + " "
            else:
                if not sentence.strip() == "":                                         
                    sentence = addPeriodWithProtectSpecificPeriod(sentence, separator)                

                convertSentence += sentence
    else:
        convertSentence = textLine     
    return convertSentence

def selectValidSentence(documentInfoOnPage, headerRatio, footerRatio):
    """Mainly remove text from table elements

    Args:
        documentInfoOnPage (_type_): 
        headerRatio (_type_): 
        footerRatio (_type_): 

    Returns:
        _type_: 
    """
    convertDocumentInfoOnPage  = {}
    for pageId, v in documentInfoOnPage.items():
        pdfDocumentBlocks = v[0]
        pageInfo = v[1]        
        convertPdfDocumentBlocks = []
        for i, pdfDocumentBlock in enumerate(pdfDocumentBlocks):

            #Exclude text that may be included in page headers and footers
            if isHeaderOrFooter(pageInfo.height, headerRatio, footerRatio, pdfDocumentBlock.y0, pdfDocumentBlock.y1):
                continue

            excludeTextLines = list(filter(lambda z: z.fontSize < pageInfo.mainFontSize, pdfDocumentBlock.pdfTextLines))            
            #Determine whether all font sizes are smaller than the main font size and decide whether to import them as text.
            if len(excludeTextLines) == len(pdfDocumentBlock.pdfTextLines):
                continue   
            
            if pdfDocumentBlock.identifier.startswith("//Document/Table"): 
                continue 

            if re.search("^\/\/Document\/.*Table", pdfDocumentBlock.identifier):            
                continue 

            convertPdfDocumentBlocks.append(pdfDocumentBlock)

        convertDocumentInfoOnPage[pageId] = (convertPdfDocumentBlocks, pageInfo)
    
    return convertDocumentInfoOnPage

def extractPageBreak(documentInfoOnPage, headerRatio, footerRatio):
    """Identify text blocks that span pages.

    Args:
        documentInfoOnPage (_type_): 
        headerRatio (_type_): 
        footerRatio (_type_): 

    Returns:
        _type_: 
    """
    convertDocumentInfoOnPage  = {}    
    excludePathFeatures = ["Figure","Table","Footnote"]

    for pageId, v in documentInfoOnPage.items():
        pdfDocumentBlocks = v[0]
        pageInfo = v[1]      
        
        if len(pdfDocumentBlocks) == 0:
            #If there are pages with only images, pages that do not have pdfDocumentBlock will appear.
            pageBreak = ""
        else:
            for i, pdfDocumentBlock in enumerate(pdfDocumentBlocks):

                #Exclude text that may be included in page headers and footers
                if isHeaderOrFooter(pageInfo.height, headerRatio, footerRatio, pdfDocumentBlock.y0, pdfDocumentBlock.y1):
                    continue

                excludeTextLines = list(filter(lambda z: z.fontSize < pageInfo.mainFontSize, pdfDocumentBlock.pdfTextLines))            
                #Determine whether all font sizes are smaller than the main font size and decide whether to import them as text.
                if len(excludeTextLines) == len(pdfDocumentBlock.pdfTextLines):
                    continue   

                if not len(list(filter(lambda x: x in pdfDocumentBlock.identifier, excludePathFeatures))) == 0:
                    continue
                
                pageBreak = pdfDocumentBlock.identifier
            
        pageInfo.pageBreakIdentifier = pageBreak
        convertDocumentInfoOnPage[pageId] = (pdfDocumentBlocks, pageInfo)

    return convertDocumentInfoOnPage


def encodePeriod(text):
    """Protects sentence delimiters with meanings other than the end of a sentence (such as a period)

    Args:
        text (_type_): 

    Returns:
        _type_: 
    """
    #I don't want to replace the last period space, so I need to mask that part.
    text = re.sub(r"\.\s$", "___###MASK1###___", text)
    #Separately mask parts that are likely to be paragraph boundaries.
    text = re.sub(r"\.\s\s", "___###MASK2###___", text)
    #protect period
    convertSentence = re.sub(PROTECT_PERIOD_INDEX_REGEX, "\g<1>" + DUMMY_REPLACE_STR_DICT["."], text)
    #cate of TextBlockString
    PROTECT_PERIOD_INDEX_REGEX2 = re.sub(r"(\.\\s)$", DUMMY_REPLACE_STR_DICT[""] + "\g<1>", PROTECT_PERIOD_INDEX_REGEX)
    convertSentence = re.sub(PROTECT_PERIOD_INDEX_REGEX2, "\g<1>" + DUMMY_REPLACE_STR_DICT["."], convertSentence)

    #Text with less than MIN_CHARACTER_NUM characters is likely not a sentence delimiter, so periods are further protected.
    convertSentence2 = ""
    for i, x in enumerate(re.split("\.\s",convertSentence)):  
        if x is None:
            continue  
        if i == 0:
            convertSentence2 = x
        else:
            if len(x) < 5:
                convertSentence2 += DUMMY_REPLACE_STR_DICT["."] + x
            else:
                convertSentence2 += ". " + x
    #undo masking
    return convertSentence2.replace("___###MASK1###___", ". ").replace("___###MASK2###___", ".  ")

def encodeSentence(text, sentenceSeparator):
    """Protects sentence delimiters with meanings other than the end of a sentence (such as a period)

    Args:
        text (_type_): _description_
        sentenceSeparator (_type_): _description_

    Returns:
        _type_: _description_
    """
    
    #Protect periods as necessary for abbreviations, index periods, etc. (English and Japanese with a dot ending)
    text = encodePeriod(text)

    #Items without sentence breaks are not supported.
    if not re.search(sentenceSeparator, text):
        return text    
    endIndices = []
    position = 0
    #Protects periods that appear within parentheses.
    #When splitting, if you give a grouped regular expression, the grouped items will also be included in the element.   
    for partialSentence in re.split(r"(\))", text):
        if partialSentence is None:
            continue
        position += len(partialSentence)
        if partialSentence == ")":
            endIndices.append(position -1)

    startIndices = []
    for idx in endIndices:
        #Find a pair of closing brackets.
        partialSentence = text[:idx]
        startIndex = findPairBracketIndex(partialSentence)
        startIndices.append(startIndex)

    #If there is something that cannot be matched with parentheses, processing is interrupted.
    if -1 in startIndices:
        return text

    finalPairs = []

    #Exclude contained (nested parentheses) ranges
    for starIdx1, endIdx1  in zip(startIndices, endIndices): 
        isInclude = False
        for starIdx2, endIdx2  in zip(startIndices, endIndices): 
            if starIdx1 > starIdx2 and endIdx1 < endIdx2:
                isInclude = True
                break
        if not isInclude:
            finalPairs.append((starIdx1, endIdx1)) 

    #Replace the periods, paying attention to the parentheses.
    convertSentence = ""
    for i, c in enumerate(text):
        hit = re.search(sentenceSeparator.replace("\s", ""), c)
        if hit:
            if c == hit.group(1):
                isReplaceOk = False
                for starIdx, endIdx  in finalPairs:
                    if i >= starIdx and i <= endIdx:
                        isReplaceOk = True                
                        break
                if isReplaceOk:                    
                    convertSentence += DUMMY_REPLACE_STR_DICT[c]                    
                else:
                    convertSentence += c 
            else:
                convertSentence += c     
        else:
            convertSentence += c 
    return convertSentence  

def splitByRegex(s):
    """Extract sentences in situations where periods do not exist as sentence breaks.

    Args:
        s (_type_): 

    Returns:
        _type_: 
    """
    regex1 = DVIDED_BY_NO_PERIOD_REGEX

    splitedElements = list(filter(lambda x: x is not None and not x.strip() == '', re.split(regex1, s)))   
    if len(splitedElements) > 1:
        textElements = []
        indexStr = ""
        for sentence in splitedElements:            
            if re.search(regex1, sentence):
                indexStr += sentence
            else:
                textElements.append(indexStr + sentence)
                textElements.append("~")
                indexStr = ""
        return textElements
    else:            
        return [s]

def divideTextByLength(textElements, sentenceSeparator, lang, deepDivideFlag):
    """Split sentences that are too long into fixed lengths

    Args:
        textElements (_type_): 
        sentenceSeparator (_type_): 
        lang (_type_): 
        deepDivideFlag (_type_): 

    Returns:
        _type_: 
    """

    #If there is a sentence that is not divided when decoding, it is divided.
    convertTextElements = textElements

    #Option: I want to separate sentences that can be separated by characters other than periods (ex. 1) (1) a) (a) etc.). If you don't take care of this, your sentences can end up being extremely long.
    if deepDivideFlag:        
        convertTextElements = []
        for s, pageId in textElements:
            convertTextElements += list(map(lambda x: (x, pageId) , splitByRegex(s)))

    #In the case of Japanese, if a sentence is too long, the predicate argument structure cannot be analyzed, so it is forcibly divided into fixed-length sentences.
    #And If a sentence is too short, string it together. (Possibly a heading index.)
    MAX_CHARACTER_NUM = 2000
    if lang == "ja_JP":
       MAX_CHARACTER_NUM =  MAX_CHARACTER_NUM_JP 

    dividedTextElements = []
    carryForwardText = ""
    for text, pageId in convertTextElements:

        evalText = carryForwardText + text
        if len(evalText) > MAX_CHARACTER_NUM:
            divideNum = math.ceil(len(evalText)/MAX_CHARACTER_NUM)
            for i in range(divideNum):
                if i == divideNum - 1:
                    #Leave the last sentence alone because no period has appeared yet.
                    carryForwardText = evalText[i*MAX_CHARACTER_NUM:]
                else:
                    #TODO: In the case of English, I want to separate the words with a space so that they are not divided by words.
                    #In English, it is necessary to investigate up to what length of character strings predicate argument structure analysis is possible.
                    dividedTextElements.append((evalText[i*MAX_CHARACTER_NUM:i*MAX_CHARACTER_NUM + MAX_CHARACTER_NUM]+"...", pageId))
                    carryForwardText = ""
        else:
            #The period in textElement comes in with a space removed.
            if re.search("^" + sentenceSeparator.replace("\s", "") + "$", text):           
                dividedTextElements.append((evalText, pageId))
                carryForwardText = ""
            elif len(text) < MIN_CHARACTER_NUM:
                #It's too short to be a sentence, so I'll string it together.
                carryForwardText = evalText + " "
            else:
                carryForwardText = evalText
    
    if len(carryForwardText) > 0:
        lastPageId = convertTextElements[-1][1]
        dividedTextElements.append((carryForwardText, lastPageId))
    
    return dividedTextElements

def decodeSentence(s):
    """Restoring a string protected with encodeSentence etc.
    """
    for k, v in DUMMY_REPLACE_STR_DICT.items():        
        s = s.replace(v, k)
    return s

def findPairBracketIndex(s):
    """parentheses pairing
    """
    result = -1
    stack = []
    for i, c in enumerate(s[::-1]): #Search from the end of the sentence.
        if c == ")":
            stack.append(c)
        elif c == "(":
            if len(stack) == 0:
                result = len(s) - i - 1
                break
            else:
                stack.pop()
    return result

def getParagraphSeparator(lang):
    """Return Regular expression to detect paragraph boundaries

    Args:
        lang (_type_): ja_JP or en_US

    Returns:
        _type_: regular expression
    """
    if lang == LANG_JP:
        return PARAGRAPH_SEPARATOR_REGEX_JP
    elif lang == LANG_EN:
        return PARAGRAPH_SEPARATOR_REGEX_EN
    else:
        return PARAGRAPH_SEPARATOR_REGEX_UNKNOWN

def getSentenceSeparator(lang):
    """Return Regular expression to detect sentence breaks

    Args:
        lang (_type_): 

    Returns:
        _type_: 
    """
    if lang == LANG_JP:
        return SENTENCE_SEPARATOR_REGEX_JP
    elif lang == LANG_EN:
        return SENTENCE_SEPARATOR_REGEX_EN
    else:
        return SENTENCE_SEPARATOR_REGEX_UNKNOWN

def getLang(text):  
    """Returns the language of the text

    Args:
        text (_type_): _description_

    Returns:
        _type_: _description_
    """
    #In this case, it cannot be determined.
    if re.search("^" + PROTECT_PERIOD_INDEX_REGEX + "$", text) or re.search("^ " + PROTECT_PERIOD_INDEX_REGEX + "$", text):
        return LANG_UNKNOWN
    
    try:
        detectedLanguage:DetectedLanguage = tc.detectLangage(text)
        return detectedLanguage.lang
    except:
        return LANG_UNKNOWN
    
    """
    if regex.search(JAPANNESE_REGEX, text):
        return LANG_JP
    else:
        if re.search(ALPHABET_NUMBER_SYMBOL_REGEX, text):
            return LANG_EN
        elif re.search(ALPHABET_REGEX, text):
            return LANG_EN
        else:
            return LANG_UNKNOWN    
    """
def normalizeLabel(s):
    """Normalize image and table labels

    Args:
        s (_type_): 

    Returns:
        _type_: 
    """
    isPrefix = True
    isNumberSymbol = False
    for i, c in enumerate(s):
        if re.search(NUMBER_SYMBOL_REGEX, c):
            isPrefix = False
            isNumberSymbol = True
        else:
            isNumberSymbol = False
        if (not isPrefix) and (not isNumberSymbol):
            return s[0:i]
    return s

def calcDistance(point1, point2):
    """Calculate the distance between two coordinates

    Args:
        point1 (_type_): _description_
        point2 (_type_): _description_

    Returns:
        _type_: _description_
    """
    p = np.array(list(point1))
    q = np.array(list(point2))
    return np.linalg.norm(p - q)

def isHeaderOrFooter(height, headerRatio, footerRatio, y0, y1):
    """Exclude text that may be included in page headers and footers

    Args:
        height (_type_): 
        headerRatio (_type_): 
        footerRatio (_type_): 
        y0 (_type_): 
        y1 (_type_): 

    Returns:
        _type_: 
    """
    headerY = height * headerRatio
    footerY = height * (1- footerRatio)
    if y0 <= headerY or y1 >= footerY:
        return True
    else:
        return False

def linkLabelAndContent(pageId, contentCoordinate, labelInfoList, usedLabels, isUpper, convergenceRadius):
    """Associating images and labels with images

    Args:
        pageId (_type_): 
        contentCoordinate (_type_): 
        labelInfoList (_type_): 
        usedLabels (_type_): 
        isUpper (bool): 
        convergenceRadius (_type_): 

    Returns:
        _type_: 
    """
    #First, filter by page number
    labelInfoListOnPage = list(filter(lambda x: x.page.pageId==pageId, labelInfoList))

    #If there is no data source, linking is not possible
    if len(labelInfoListOnPage) == 0:
        return "", [], np.inf
    
    pointContent = (contentCoordinate.x0, contentCoordinate.y1)
    if isUpper:
        pointContent = (contentCoordinate.x0, contentCoordinate.y0)
    
    minDistance = np.inf
    label = ""
    metaList = []
    for labelInfo in labelInfoListOnPage:
        topPointLabel = (labelInfo.coodinate.x0, labelInfo.coodinate.y0)        
        neighborhood =  calcDistance(pointContent, topPointLabel)
        if neighborhood < convergenceRadius and neighborhood < minDistance and not labelInfo.label in usedLabels:
            minDistance = neighborhood
            label = labelInfo.label
            metaList = labelInfo.metaList
    return label, metaList, minDistance
 
def getLabels(text, isCaption):
    """Extract labels used for images and tables from text

    Args:
        text (_type_): 
        isCaption (bool): 

    Returns:
        _type_: 
    """
    LABEL_REGEX = LABEL_REGEX_IN_SENTENCE
    if isCaption:
        LABEL_REGEX = LABEL_REGEX
    labels = []   
    tmpText = text 
    while True:
        tmpText = mojimoji.zen_to_han(tmpText, kana=False).lower() 
        tmpText = unicodedata.normalize('NFKC', tmpText)                       
        hit = re.search(LABEL_REGEX, tmpText)
        if not hit:
            break
        label = normalizeLabel(hit.group(1).replace(" ", ""))        
        labels.append(label)
        tmpText = tmpText.replace(hit.group(1), "")
    return labels

def existLabel(text, isCaption):
    """Check if text contains labels used for images and tables

    Args:
        text (_type_): 
        isCaption (bool): 

    Returns:
        _type_: 
    """
    LABEL_REGEX = LABEL_REGEX_IN_SENTENCE
    if isCaption:
        LABEL_REGEX = LABEL_REGEX

    if text is None:
        return False
    text = mojimoji.zen_to_han(text, kana=False).lower() 
    text = unicodedata.normalize('NFKC', text)                                   
    if re.search(LABEL_REGEX, text):
        return True
    else:
        return False

def convertJpeg(filename, id, saveDir):  
    """Jpegファイルへの変換

    Args:
        filename (_type_): 
        id (_type_): 
        saveDir (_type_): 

    Returns:
        _type_: 
    """
    im = Image.open(filename)
    jpegFilename = saveDir + id + ".jpg"
    im = im.convert("RGB")
    im.save(jpegFilename)
    return jpegFilename, im.width, im.height
