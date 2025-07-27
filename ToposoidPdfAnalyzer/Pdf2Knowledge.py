
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

import ToposoidCommon as tc
from .PdfMergeContents import mergePdfContents 
from ToposoidCommon.model import Propositions
import uuid
import traceback

LOG = tc.LogUtils(__name__)

class Pdf2Knowledge(): 
    """Main class that converts PDF convert into Toposoid knowledge.
    """
    def pdf2Knowledge(self, documentId, filename, transversalState, headerRatio=0.05, footerRatio=0.05, deepDivideFlag=False, isTest=False):
        try:
            LOG.info("pdf2Knowledge started", transversalState)
            propositions = mergePdfContents(documentId, filename, transversalState, headerRatio=headerRatio, footerRatio=footerRatio, deepDivideFlag=deepDivideFlag, isTest=isTest)            
            LOG.info("pdf2Knowledge completed", transversalState)
            return Propositions(propositions=propositions)
        except Exception as e:
            LOG.error(traceback.format_exc(), transversalState)
            raise e
