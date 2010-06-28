import os
from pymel import versions
from pymel import core as pm
import maya.cmds as mc
import oyAuxiliaryFunctions as oyAux
from oyProjectManager.models import asset, project, repository, abstractClasses



__version__ = "10.6.28"






########################################################################
class MayaEnvironment(abstractClasses.Environment):
    """the maya environment class
    """
    
    
    
    #----------------------------------------------------------------------
    def save(self):
        """the save action for maya environment

        uses PyMel to save the file (not necessary but comfortable )
        """
        
        # set asset extension
        self._asset.extension = 'ma'
        
        # set the project to the current environment
        pm.workspace.open( self._asset.sequenceFullPath )
        
        # set the render file name and version
        self.setRenderFileName()
        
        # set the playblast file name
        self.setPlayblastFileName()
        
        # create the folder if it doesn't exists
        oyAux.createFolder( self._asset.path )
        
        # delete the unknown nodes
        unknownNodes = pm.ls(type='unknown')
        pm.delete( unknownNodes )
        
        # save the file
        pm.saveAs( self._asset.fullPath, type='mayaAscii' )
        
        # append it to the recent file list
        self.appendToRecentFiles( self._asset.fullPath )
        
        return True
    
    
    
    #----------------------------------------------------------------------
    def export(self):
        """the export action for maya environment
        """
        
        # check if there is something selected
        if len(pm.ls(sl=True)) < 1:
            print "selection error"
            return False
        
        # set the extension to ma by default
        self._asset.extension = 'ma'
        
        # create the folder if it doesn't exists
        oyAux.createFolder( self._asset.path )
        
        # export the file
        pm.exportSelected( self._asset.fullPath, type='mayaAscii' )
        
        return True
    
    
    
    #----------------------------------------------------------------------
    def open_(self, force=False):
        """the open action for maya environment
        
        returns assets those needs to be updated as a list of asset objects
        """
        
        # check for unsaved changes
        assetFullPath = self._asset.fullPath
        
        pm.openFile( assetFullPath, f=force, loadReferenceDepth='none' )
        
        # set the project
        pm.workspace.open( self._asset.sequenceFullPath )
        
        # set the playblast folder
        self.setPlayblastFileName()
        
        self.appendToRecentFiles( assetFullPath )
        
        # check the referenced assets for newer version
        toUpdateList = self.checkReferenceVersions()
        
        return True, toUpdateList
    
    
    
    #----------------------------------------------------------------------
    def import_(self):
        """the import action for maya environment
        """
        pm.importFile( self._asset.fullPath )
        
        return True
    
    
    
    #----------------------------------------------------------------------
    def reference(self):
        """the reference action for maya environment
        """
        
        # use the file name without extension as the namespace
        nameSpace = self._asset.fileNameWithoutExtension
        
        pm.createReference( self._asset.fullPath, gl=True, loadReferenceDepth='all', namespace=nameSpace, options='v=0')
        
        return True
    
    
    
    #----------------------------------------------------------------------
    def getPathVariables(self):
        """gets the file name from maya environment
        """
        
        foundValidAsset = False
        readRecentFile = True
        fileName = path = None
        workspacePath = None
        
        repo = repository.Repository()
        
        fullPath = pm.env.sceneName()
        if os.name == 'nt':
            fullPath = fullPath.replace('/','\\')
        
        #print "the fullPath in maya is ", fullPath
        
        if fullPath != '':
            fileName = os.path.basename( fullPath )
            
            # try to create an asset with that info
            projName, seqName = repo.getProjectAndSequenceNameFromFilePath( fullPath )
            
            proj = project.Project( projName )
            seq = project.Sequence( proj, seqName )
            
            testAsset = asset.Asset( proj, seq, fileName )
            
            if testAsset.isValidAsset:
                fileName = testAsset.fileName
                path = testAsset.path
                readRecentFile = False
        
        
        
        if readRecentFile:
            # read the fileName from recent files list
            # try to get the a valid asset file from starting the last recent file
            
            try:
                recentFiles = pm.optionVar['RecentFilesList']
            except KeyError:
                print "no recent files"
                recentFiles = None
            
            if recentFiles is not None:
                
                for i in range(len(recentFiles)-1, -1,-1):
                    
                    fileName = os.path.basename( recentFiles[i] )
                    projName, seqName = repo.getProjectAndSequenceNameFromFilePath( recentFiles[i] )
                    
                    if projName != None and seqName != None:
                        
                        proj = project.Project( projName )
                        seq = project.Sequence( proj, seqName )
                        
                        testAsset = asset.Asset( proj, seq, fileName )
                        
                        if testAsset.isValidAsset and testAsset.exists:
                            path = testAsset.path
                            foundValidAsset = True
                            break
                        
            # get the workscape path
            workspacePath = self.getWorkspacePath()
            returnWorkspace = False
            
            if foundValidAsset:
                #print "found a valid asset with path", path
                # check if the recent files path matches the current workspace
                if not path.startswith( workspacePath ):
                    # use the workspacePath
                    returnWorkspace = True
            else:
                # just get the path from workspace and return an empty fileName
                returnWorkspace = True
                
            if returnWorkspace:
                fileName = None
                path = workspacePath
                
                
        return fileName, path



    #----------------------------------------------------------------------
    def setRenderFileName(self):
        """sets the render file name
        """
        
        # check/load Mentalray
        #if pm.pluginInfo(
        
        parentSeq = self._asset.sequence
        
        renderOutputFolder = parentSeq.structure.getOutputFolderPathOf( 'RENDER' ) # _RENDERED_IMAGES_/SHOTS
        
        # image folder from the workspace.mel
        imageFolderFromWS = pm.workspace.fileRules['image'] # _RENDERED_IMAGES_/
        
        shotFolder = renderOutputFolder[ len(imageFolderFromWS):] # SHOTS
        
        assetBaseName = self._asset.baseName
        
        renderFileName = ''
        if parentSeq.noSubNameField:
            renderFileName = shotFolder + "/" + assetBaseName + "/<Layer>/" + assetBaseName + "_<Layer>_<RenderPass>_<Version>"
        else: # remove later when the support for old project is over
            assetSubName = self._asset.subName
            renderFileName = shotFolder + "/" + assetBaseName + "/" + assetSubName + "/<Layer>/" + assetBaseName + "_" + assetSubName + "_<Layer>_<RenderPass>_<Version>"
        
        # SHOTS/ToonShading/TestTransition/incidence/ToonShading_TestTransition_incidence_MasterPass_v050.####.iff
        
        # defaultRenderGlobals
        dRG = pm.PyNode('defaultRenderGlobals')
        dRG.setAttr('imageFilePrefix', renderFileName)
        dRG.setAttr('renderVersion', self._asset.versionString )
        dRG.setAttr('animation', 1)
        dRG.setAttr('outFormatControl', 0 )
        dRG.setAttr('extensionPadding', 3 )
        dRG.setAttr('pff', 1)



    #----------------------------------------------------------------------
    def setPlayblastFileName(self):
        """sets the playblast file name
        """
        
        playblastFolderPath = self._asset.type.playblastFolder
        
        #if os.name == 'nt':
            #playblastFolderPath = playblastFolderPath.replace('/','\\')
        
        assert(isinstance(self._asset, asset.Asset))
        
        seqFullPath = self._asset.sequence.fullPath
        
        baseName = self._asset.baseName
        
        playblastPath = os.path.join( seqFullPath, playblastFolderPath, baseName )
        playblastFullPath = os.path.join( playblastPath, self._asset.fileNameWithoutExtension )
        
        # create the folder
        oyAux.createFolder( playblastPath )
        
        playblastFullPath = playblastFullPath.replace('\\','/')
        #print "playblastFullPath:",playblastFullPath
        
        pm.optionVar['playblastFile'] = playblastFullPath
    
    
    
    #----------------------------------------------------------------------
    def setProject(self, projectName, sequenceName ):
        """sets the project
        """
        repo = repository.Repository()
        
        mayaProjectPath = os.path.join( repo.projectsFullPath, projectName, sequenceName )
        
        pm.workspace.open(mayaProjectPath)
        
        proj = project.Project( projectName )
        seq = project.Sequence( proj, sequenceName )
        
        # set the current timeUnit to match with the environments
        self.setTimeUnit( seq.timeUnit )
    
    
    
    #----------------------------------------------------------------------
    def getWorkspacePath(self):
        """returns the workspace path
        tries to fix the path separator for windows
        """
        
        path = pm.workspace.name
        
        if os.name == 'nt':
            path = path.replace('/','\\')
        
        return path
    
    
    
    #----------------------------------------------------------------------
    def appendToRecentFiles(self, path):
        """appends the given path to the recent files list
        """
        
        # add the file to the recent file list
        try:
            recentFiles = pm.optionVar['RecentFilesList']
        except KeyError:
            # there is no recent files list so create one
            # normally it is Maya's job
            # but somehow it is not working for new installations
            recentFiles = pm.OptionVarList( [], 'RecentFilesList' )
            
        #assert(isinstance(recentFiles,pm.OptionVarList))
        recentFiles.appendVar( path )



    #----------------------------------------------------------------------
    def checkReferenceVersions(self):
        """checks the referenced assets versions
        
        returns a list of asset and maya reference objects in a tupple
        """
        
        # get all the valid asset references
        assetTupleList = self.getReferencedAssets()
        
        updateList = []
        
        for assetTuple in assetTupleList:
            #assert(isinstance(asset, asset.Asset))
            
            asset = assetTuple[0]
            
            if not asset.isLatestVersion():
                # add asset to the update list
                updateList.append( assetTuple )
            
        #return updateList
        
        # sort the list according to assetFilepath
        return sorted( updateList, None, lambda x: x[2] )



    #----------------------------------------------------------------------
    def getReferencedAssets(self):
        """returns the valid assets those been referenced to the current scene
        
        returns asset objects and the corresponding reference object as a
        tupple in a list, and a string showing the path of the reference
        """
        
        validAssets = []
        
        # get all the references
        allReferences = pm.listReferences()
        
        # create a repository object
        repo = repository.Repository()
        
        osName = os.name
        
        refsAndPaths = []
        # iterate over them to find valid assets
        for ref in allReferences:
            # it is a dictionary
            
            #assert(isinstance(ref, pm.FileReference))
            tempAssetFullPath = ref.path
            if osName == 'nt':
                tempAssetFullPath = tempAssetFullPath.replace('/','\\')
            
            refsAndPaths.append( (ref, tempAssetFullPath) )
        
        # sort them according to path
        # to make same paths togather
        
        refsAndPaths = sorted( refsAndPaths, None, lambda x: x[1])
        
        prevAsset = None
        prevFullPath = ''
        
        for ref, fullPath in refsAndPaths:
            
            if fullPath == prevFullPath:
                # directly append the asset to the list
                validAssets.append( (prevAsset, ref, prevFullPath ) )
            else:
                projName, seqName = repo.getProjectAndSequenceNameFromFilePath( fullPath )
                
                proj = project.Project( projName )
                seq = project.Sequence( proj, seqName )
                
                tempAssetPath = os.path.basename( fullPath )
                tempAsset = asset.Asset( proj, seq, tempAssetPath )
                
                if tempAsset.isValidAsset:
                    validAssets.append( (tempAsset, ref, fullPath) )
                    
                    prevAsset = tempAsset
                    prevFullPath = fullPath
                    
        # return a sorted list
        return sorted( validAssets, None, lambda x: x[2] )
    
    
    
    
    #----------------------------------------------------------------------
    def updateAssets(self, assetTupleList):
        """update assets to the latest version
        """
        
        previousAssetPath = ''
        
        for assetTuple in assetTupleList:
            
            asset = assetTuple[0]
            ref = assetTuple[1]
            assetPath =  assetTuple[2]
            
            #assert(isinstance(asset, asset.Asset))
            #assert(isinstance(ref, pm.FileReference))
            
            if assetPath != previousAssetPath:
                latestAsset = asset.latestVersion2[0]
                previousAssetPath = assetPath
            
            ref.replaceWith( latestAsset.fullPath )
    
    
    
    #----------------------------------------------------------------------
    def getFrameRange(self):
        """returns the current playback frame range
        """
        startFrame = int( pm.playbackOptions(q=True, ast=True) )
        endFrame = int( pm.playbackOptions(q=True, aet=True) )
        return startFrame, endFrame
    
    
    
    #----------------------------------------------------------------------
    def setFrameRange(self, startFrame=1, endFrame=100, adjust_frame_range=False):
        """sets the start and end frame range
        """
        
        # set it in the playback
        pm.playbackOptions(ast=startFrame, aet=endFrame)
        
        if adjust_frame_range:
            pm.playbackOptions( min=startFrame, max=endFrame )
        
        # set in the render range
        dRG = pm.PyNode('defaultRenderGlobals')
        dRG.setAttr('startFrame', startFrame )
        dRG.setAttr('endFrame', endFrame )
    
    
    
    #----------------------------------------------------------------------
    def getTimeUnit(self):
        """returns the timeUnit of the environment
        """
        
        # return directly from maya, it uses the same format
        return (pm.currentUnit(q=1, t=1)).lower()
    
    
    
    #----------------------------------------------------------------------
    def setTimeUnit(self, timeUnit='pal'):
        """sets the timeUnit of the environment
        """
        
        # check if the given unit is in repository
        repo = repository.Repository()
        
        if not repo.timeUnits.has_key( timeUnit ):
            raise KeyError(timeUnit)
        
        # get the current time, current playback min and max ( because maya
        # changes them, try to restore the limits )
        
        currentTime = pm.currentTime(q=1)
        pMin = pm.playbackOptions(q=1, min=1)
        pMax = pm.playbackOptions(q=1, max=1)
        pAst = pm.playbackOptions(q=1, ast=1)
        pAet = pm.playbackOptions(q=1, aet=1)
        
        # set the time unit, do not change the keyframe times
        # use the timeUnit as it is
        pm.currentUnit( t=timeUnit, ua=0 )
        # to be sure
        pm.optionVar['workingUnitTime'] = timeUnit
        
        
        # update the playback ranges
        pm.currentTime( currentTime )
        pm.playbackOptions( ast=pAst, aet=pAet )
        pm.playbackOptions( min=pMin, max=pMax )



    #----------------------------------------------------------------------
    def loadReferences(self):
        """loads all the references
        """
        
        # get all the references
        allReferences = pm.listReferences()
        
        for reference in allReferences:
            reference.load()
    
    
    
    #----------------------------------------------------------------------
    def replaceAssets(self, sourceRef, targetFile):
        """replaces the source asset with the target asset
        
        the sourceAsset may should be in maya reference node
        """
        
        # get the reference node
        baseRefNode = sourceRef.refNode
        
        # get the base namespace before replacing the reference
        prevNS = self.getFullNamespaceFromNodeName( sourceRef.nodes()[0] )
        
        # if the sourceRef has referenced files do a dirty edit
        # by applying all the edits to the referenced node (the old way of
        # replacing references )
        subReferences = self.getAllSubReferences( sourceRef )
        if len(subReferences) > 0:
            # for all subReferences get the editString and apply it to the
            # replaced file with new namespace
            allEdits = []
            for subRef in subReferences:
                allEdits += subRef.getReferenceEdits( orn= baseRefNode )
            
            # replace the reference
            sourceRef.replaceWith( targetFile )
            
            # try to find the new namespace
            subReferences = self.getAllSubReferences( sourceRef )
            newNS = self.getFullNamespaceFromNodeName( subReferences[0].nodes()[0] ) # possible bug here, fix it later
            
            # replace the old namespace with the new namespace in all the edits
            allEdits = [ edit.replace( prevNS+":", newNS+":") for edit in allEdits ] 
            
            # apply all the edits
            for edit in allEdits:
                try:
                    pm.mel.eval( edit )
                except pm.MelError:
                    pass
            
        else:
            
            # replace the reference
            sourceRef.replaceWith( targetFile )
            
            # try to find the new namespace
            subReferences = self.getAllSubReferences( sourceRef )
            newNS = self.getFullNamespaceFromNodeName( subReferences[0].nodes()[0] ) # possible bug here, fix it later
            
            
            #subReferences = sourceRef.subReferences()
            #for subRefData in subReferences.iteritems():
                #refNode = subRefData[1]
                #newNS = self.getFullNamespaceFromNodeName( refNode.nodes()[0] )
            
            # if the new namespace is different than the previous one
            # also change the edit targets
            if prevNS != newNS:
                # debug
                print "prevNS", prevNS
                print "newNS ", newNS
                
                # get the new sub references
                for subRef in self.getAllSubReferences( sourceRef ):
                    # for all the nodes in sub references
                    # change the edit targets with new namespace
                    for node in subRef.nodes():
                        # use the long name -- suggested by maya help
                        nodeNewName = node.longName()
                        nodeOldName = nodeNewName.replace( newNS+':', prevNS+':')
                        
                        pm.referenceEdit( baseRefNode, changeEditTarget=( nodeOldName, nodeNewName) )
                        #pm.referenceEdit( baseRefNode, orn=baseRefNode, changeEditTarget=( nodeOldName, nodeNewName) )
                        #pm.referenceEdit( subRef, orn=baseRefNode, changeEditTarget=( nodeOldName, nodeNewName ) )
                        #for aRefNode in pm.ls(type='reference'):
                            #if len(aRefNode.attr('sharedReference').listConnections(s=0,d=1)) == 0: # not a shared reference
                                #pm.referenceEdit( aRefNode, orn=baseRefNode, changeEditTarget=( nodeOldName, nodeNewName), scs=1, fld=1 )
                                ##pm.referenceEdit( aRefNode, applyFailedEdits=True )
                    #pm.referenceEdit( subRef, applyFailedEdits=True )
                    
                    
                # apply all the failed edits again
                pm.referenceEdit( baseRefNode, applyFailedEdits=True )
    
    
    
    #----------------------------------------------------------------------
    def getAllSubReferences(self, ref):
        """returns the recursive sub references as a list of FileReference
        objects for the given file reference
        """
        
        allRefs = []
        subRefDict = ref.subReferences()
        
        if len(subRefDict) > 0:
            for subRefData in subRefDict.iteritems():
                
                # first convert the sub ref dictionary to a normal ref object
                subRef = subRefData[1]
                allRefs.append( subRef )
                allRefs += self.getAllSubReferences( subRef )
        
        return allRefs
    
    
    
    #----------------------------------------------------------------------
    def getFullNamespaceFromNodeName(self, node):
        """dirty way of getting the namespace from node name
        """
        
        return ':'.join( (node.name().split(':'))[:-1] )
        