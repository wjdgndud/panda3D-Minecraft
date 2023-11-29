from math import pi, sin, cos

from panda3d.core import loadPrcFile
from direct.showbase.ShowBase import ShowBase
from panda3d.core import DirectionalLight, AmbientLight
from panda3d.core import CollisionTraverser, CollisionNode, CollisionBox, CollisionRay, CollisionHandlerQueue, CollisionHandlerPusher, BitMask32
from panda3d.core import WindowProperties
from panda3d.core import TransparencyAttrib
from direct.gui.DirectGui import *
from direct.gui.OnscreenImage import OnscreenImage 


loadPrcFile('settings.prc')

def degToRad(degrees):
    return degrees * (pi / 180.0)

class Game(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        self.selectedBlockType = 'grass'

        self.loadModels()
        self.setupLights()
        self.setupCamera()
        self.setupPauseScreen()
        self.setupSkybox()
        self.generateWorld()
        self.setupControls()
        self.captureMouse()
        self.setupTasks()

    def update(self, task):
        dt = globalClock.getDt()

        self.movePlayer(dt)

        if self.cameraSwingActivated:
            self.moveCameraWithMouse(dt)

        return task.cont

    def movePlayer(self, dt):
        playerMoveSpeed = 10

        x_movement = 0
        y_movement = 0
        z_movement = 0

        if self.keyMap['forward']:
            x_movement -= dt * playerMoveSpeed * sin(degToRad(camera.getH()))
            y_movement += dt * playerMoveSpeed * cos(degToRad(camera.getH()))
        if self.keyMap['backward']:
            x_movement += dt * playerMoveSpeed * sin(degToRad(camera.getH()))
            y_movement -= dt * playerMoveSpeed * cos(degToRad(camera.getH()))
        if self.keyMap['left']:
            x_movement -= dt * playerMoveSpeed * cos(degToRad(camera.getH()))
            y_movement -= dt * playerMoveSpeed * sin(degToRad(camera.getH()))
        if self.keyMap['right']:
            x_movement += dt * playerMoveSpeed * cos(degToRad(camera.getH()))
            y_movement += dt * playerMoveSpeed * sin(degToRad(camera.getH()))
        if self.keyMap['up']:
            z_movement += dt * playerMoveSpeed
        if self.keyMap['down']:
            z_movement -= dt * playerMoveSpeed

        camera.setPos(
            camera.getX() + x_movement,
            camera.getY() + y_movement,
            camera.getZ() + z_movement,
        )

    def moveCameraWithMouse(self, dt):
        cameraSwingFactor = 10

        md = self.win.getPointer(0)
        mouseX = md.getX()
        mouseY = md.getY()
        mouseChangeX = mouseX - self.lastMouseX
        mouseChangeY = mouseY - self.lastMouseY

        currentH = self.camera.getH()
        currentP = self.camera.getP()

        self.camera.setHpr(
            currentH - mouseChangeX * dt * cameraSwingFactor,
            min(90, max(-90, currentP - mouseChangeY * dt * cameraSwingFactor)),
            0
        )

        self.lastMouseX = mouseX
        self.lastMouseY = mouseY

    def setupTasks(self):
        taskMgr.add(self.update, 'update')

    def setupCamera(self):
        self.disableMouse()

        self.camera.setPos(0, 0, 3)
        self.camLens.setFov(80)
        self.camLens.setNear(0.25)

        icon = OnscreenImage(image = "crosshairs.png",
                        pos = (0, 0, 0),
                        scale = 0.05)
        icon.setTransparency(TransparencyAttrib.MAlpha)

        self.cTrav = CollisionTraverser()
        ray = CollisionRay()
        ray.setFromLens(self.camNode, (0, 0))
        rayNode = CollisionNode("cameraLookAtRay")
        rayNode.addSolid(ray)
        rayNodePath = self.camera.attachNewNode(rayNode)
        self.rayQueue = CollisionHandlerQueue()
        rayMask = BitMask32()
        rayMask.setBit(1)
        rayNode.setIntoCollideMask(rayMask)
        rayNode.setFromCollideMask(rayMask)
        self.cTrav.addCollider(rayNodePath, self.rayQueue)

        playerCollisionBox = CollisionBox((-0.5, -0.5, -3), (0.5, 0.5, 0))
        playerCollisionBoxNode = CollisionNode("playerBox")
        playerCollisionBoxNode.addSolid(playerCollisionBox)

        # We need to prevent this from colliding with "line of sight" ray
        playerMask = BitMask32()
        playerMask.setBit(2)
        playerCollisionBoxNode.setIntoCollideMask(playerMask)
        playerCollisionBoxNode.setFromCollideMask(playerMask)

        playerCollider = self.camera.attachNewNode(playerCollisionBoxNode)
        pusher = CollisionHandlerPusher()
        pusher.addCollider(playerCollider, self.camera)
        self.cTrav.addCollider(playerCollider, pusher) 

    def setupControls(self):
        self.keyMap = {
            "forward" : False,
            "backward" : False,
            "left" : False,
            "right" : False,
            "up" : False,
            "down" : False,
        }

        self.accept("w", self.updateKeyMap, ["forward", True])
        self.accept("w-up", self.updateKeyMap, ["forward", False])
        self.accept("s", self.updateKeyMap, ["backward", True])
        self.accept("s-up", self.updateKeyMap, ["backward", False])
        self.accept("a", self.updateKeyMap, ["left", True])
        self.accept("a-up", self.updateKeyMap, ["left", False])
        self.accept("d", self.updateKeyMap, ["right", True])
        self.accept("d-up", self.updateKeyMap, ["right", False])
        self.accept("space", self.updateKeyMap, ["up", True])
        self.accept("space-up", self.updateKeyMap, ["up", False])
        self.accept("lshift", self.updateKeyMap, ["down", True])
        self.accept("lshift-up", self.updateKeyMap, ["down", False])

        self.accept("mouse1", self.handleLeftClick)
        self.accept("mouse3", self.handleRightClick)

        self.accept("1", self.setSelectedBlockType, ['grass'])
        self.accept("2", self.setSelectedBlockType, ['dirt'])
        self.accept("3", self.setSelectedBlockType, ['stone'])
        self.accept("4", self.setSelectedBlockType, ['sand'])

        self.accept('escape', self.releaseMouse)
    
    def setSelectedBlockType(self, type):
        self.selectedBlockType = type
    
    def updateKeyMap(self, controlName, controlState):
        self.keyMap[controlName] = controlState

    def addNewBlock(self, type, x, y, z):
        newBlockNode = render.attachNewNode("new-box-placeholder")

        newBlockNode.setPos(x, y, z)

        if type == 'grass':
            self.grassBlock.instanceTo(newBlockNode)
        elif type == 'dirt':
            self.dirtBlock.instanceTo(newBlockNode)
        elif type == 'stone':
            self.stoneBlock.instanceTo(newBlockNode)
        elif type == 'sand':
            self.sandBlock.instanceTo(newBlockNode)

        blockSolid = CollisionBox((-1, -1, -1),  (1, 1, 1)) # These diagonal points are RELATIVE to the node you add the solid to, NOT absolute coords
        blockNode = CollisionNode(f"block-{x}-{y}")
        blockNode.addSolid(blockSolid)
        blockMask = BitMask32()
        blockMask.setBit(1) # We want blocks to collide with both the "line of sight" ray AND...
        blockMask.setBit(2) # ...the player's box
        blockNode.setFromCollideMask(blockMask)
        collider = newBlockNode.attachNewNode(blockNode)
        collider.setPythonTag("owner", newBlockNode) 

    def handleLeftClick(self):
        self.removeBlock()

    def handleRightClick(self):
        self.placeBlock()

    def placeBlock(self):
        if self.rayQueue.getNumEntries() > 0:
            self.rayQueue.sortEntries()
            rayHit = self.rayQueue.getEntry(0)
            normal = rayHit.getSurfaceNormal(rayHit.getIntoNodePath())

            hitNodePath = rayHit.getIntoNodePath()
            if hitNodePath.hasPythonTag("owner"):
                hitObject = hitNodePath.getPythonTag("owner")
                distanceFromPlayer = hitObject.getDistance(self.camera)

                if distanceFromPlayer < 14:
                    hitBoxPos = hitObject.getPos()
                    blockSize = 2

                    newBlockPos = hitBoxPos + normal * blockSize
                    self.addNewBlock(self.selectedBlockType, newBlockPos.x, newBlockPos.y, newBlockPos.z)

    def removeBlock(self):
        if self.rayQueue.getNumEntries() > 0:
            self.rayQueue.sortEntries()
            rayHit = self.rayQueue.getEntry(0)

            hitNodePath = rayHit.getIntoNodePath()
            if hitNodePath.hasPythonTag("owner"):
                hitObject = hitNodePath.getPythonTag("owner")
                distanceFromPlayer = hitObject.getDistance(self.camera)

                if distanceFromPlayer < 12:
                    hitNodePath.clearPythonTag("owner")
                    hitObject.removeNode()
    
    def captureMouse(self):
        md = self.win.getPointer( 0 )
        self.lastMouseX = md.getX()
        self.lastMouseY = md.getY()

        self.cameraSwingActivated = True
        properties = WindowProperties()
        properties.setCursorHidden(True)
        properties.setMouseMode(WindowProperties.M_relative)
        self.win.requestProperties(properties)
        self.pauseScreen.hide()

    def releaseMouse(self):
        self.cameraSwingActivated = False
        properties = WindowProperties()
        properties.setCursorHidden(False)
        properties.setMouseMode(WindowProperties.M_absolute)
        self.win.requestProperties(properties)
        self.pauseScreen.show()
    
    def setupPauseScreen(self):
        self.pauseScreen = DirectDialog(text = 'Paused...',
                                frameSize = (-0.7, 0.7, -0.7, 0.7),
                                fadeScreen = 0.4,
                                relief = DGG.FLAT)
                            
        btn = DirectButton(text = "Resume",
            command = self.captureMouse,
            pos = (0, 0, -0.2),
            parent = self.pauseScreen,
            scale = 0.05)

        self.pauseScreen.hide()

    def loadModels(self):
        self.dirtBlock = loader.loadModel('dirt-block.glb')
        self.stoneBlock = loader.loadModel('stone-block.glb')
        self.grassBlock = loader.loadModel('grass-block.glb')
        self.sandBlock = loader.loadModel('sand-block.glb')

    def setupSkybox(self):
        self.skybox = loader.loadModel('skybox/skybox.egg')
        self.skybox.setScale(512)
        self.skybox.setBin('background', 1)
        self.skybox.setDepthWrite(0)
        self.skybox.setLightOff()
        self.skybox.reparentTo(render)

    def generateWorld(self):
        for z in range(10):
            for x in range(20):
                for y in range(20):
                    self.addNewBlock(
                        'grass' if z == 0 else 'dirt',
                        x * 2 - 20,
                        y * 2 - 20,
                        -z * 2,
                    )

    def setupLights(self):
        mainLight = DirectionalLight('main light')
        mainLightNodePath = render.attachNewNode(mainLight)
        mainLightNodePath.setHpr(30, -60, 0)
        render.setLight(mainLightNodePath)

        ambientLight = AmbientLight('ambient light')
        ambientLight.setColor((0.3, 0.3, 0.3, 1))
        ambientLightNodePath = render.attachNewNode(ambientLight)
        render.setLight(ambientLightNodePath)


game = Game()
game.run()