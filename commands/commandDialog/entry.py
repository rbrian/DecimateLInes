from math import pi
from urllib.request import OpenerDirector
import adsk.core
import adsk.fusion
import os
from ...lib import fusion360utils as futil
from ... import config
app = adsk.core.Application.get()
ui = app.userInterface

# TODO *** Specify the command identity information. ***
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_cmdDialog'
CMD_NAME = 'Project Decimated'
CMD_Description = 'Project a profile that has been simplified by removing unnecessary points'

# Specify that the command will be promoted to the panel.
IS_PROMOTED = True

# TODO *** Define the location where the command button will be created. ***
# This is done by specifying the workspace, the tab, and the panel, and the
# command it will be inserted beside. Not providing the command to position it
# will insert it at the end.
WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'SketchCreatePanel'
COMMAND_BESIDE_ID = 'Include3DGeometry'
SEPARATOR_ID = f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_Separator"
PTCOUNT_ID = f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_PtCount"
DIST_SLIDER_ID = f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_DistSlider"
ANGLE_SLIDER_ID = f"{config.COMPANY_NAME}_{config.ADDIN_NAME}_AngleSlider"
SELECTOR_ID = "selection_input"

# Resource location for command icons, here we assume a sub folder in this directory named "resources".
ICON_FOLDER = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), 'resources', '')

LINELIST = []
DO_RESCAN = False
MYGRAPHICS = None

# Local list of event handlers used to maintain a reference so
# they are not released and garbage collected.
local_handlers = []


# Executed when add-in is run.
def start():
    # Create a command Definition.
    cmd_def = ui.commandDefinitions.addButtonDefinition(
        CMD_ID, CMD_NAME, CMD_Description, ICON_FOLDER)

    # Define an event handler for the command created event. It will be called when the button is clicked.
    futil.add_handler(cmd_def.commandCreated, command_created)

    # ******** Add a button into the UI so the user can run the command. ********
    # Get the target workspace the button will be created in.
    workspace = ui.workspaces.itemById(WORKSPACE_ID)

    # Get the panel the button will be created in.
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    drop = panel.controls.itemById("ProjectIncludeDropDown")
    # Create the button command control in the UI after the specified existing command.
    control = drop.controls.addCommand(cmd_def, COMMAND_BESIDE_ID, True)
    sep = drop.controls.addSeparator(SEPARATOR_ID, COMMAND_BESIDE_ID, True)

    # Specify if the command is promoted to the main toolbar.
    control.isPromoted = IS_PROMOTED


# Executed when add-in is stopped.
def stop():
    # Get the various UI elements for this command
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    drop = panel.controls.itemById("ProjectIncludeDropDown")
    command_control = drop.controls.itemById(CMD_ID)
    command_definition = ui.commandDefinitions.itemById(CMD_ID)
    sep = drop.controls.itemById(SEPARATOR_ID)

    # Delete the separator
    if sep:
        sep.deleteMe()

    # Delete the button command control
    if command_control:
        command_control.deleteMe()

    # Delete the command definition
    if command_definition:
        command_definition.deleteMe()


# Function that is called when a user clicks the corresponding button in the UI.
# This defines the contents of the command dialog and connects to the command related events.
def command_created(args: adsk.core.CommandCreatedEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Created Event')

    args.command.setDialogInitialSize(400, 100)

    # https://help.autodesk.com/view/fusion360/ENU/?contextId=CommandInputs
    inputs = args.command.commandInputs

    # TODO Define the dialog for your command by adding different inputs to the command.
    selector = inputs.addSelectionInput(
        SELECTOR_ID, "Select Line", "Select line")

    selector.addSelectionFilter(adsk.core.SelectionCommandInput.SketchLines)
    selector.setSelectionLimits(1)

    ptcount = inputs.addStringValueInput(PTCOUNT_ID, "Points", "")
    ptcount.isReadOnly = True

    slider = inputs.addFloatSliderCommandInput(
        DIST_SLIDER_ID, "Min Distance", "mm", 0.0001, 1, False)
    slider.valueOne = 0.01

    angle = inputs.addAngleValueCommandInput(
        ANGLE_SLIDER_ID, "Angle tolerance", adsk.core.ValueInput.createByString("1"))

    # TODO Connect to the events that are needed by this command.
    futil.add_handler(args.command.execute, command_execute,
                      local_handlers=local_handlers)
    futil.add_handler(args.command.inputChanged,
                      command_input_changed, local_handlers=local_handlers)
    futil.add_handler(args.command.executePreview,
                      command_preview, local_handlers=local_handlers)
    futil.add_handler(args.command.validateInputs,
                      command_validate_input, local_handlers=local_handlers)
    futil.add_handler(args.command.destroy, command_destroy,
                      local_handlers=local_handlers)


# This event handler is called when the user clicks the OK button in the command dialog or
# is immediately called after the created event not command inputs were created for the dialog.
def command_execute(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Execute Event')

    # TODO ******************************** Your code here ********************************

    # Get a reference to your command's inputs.
    inputs = args.command.commandInputs

    global LINELIST

    if DO_RESCAN:
        LINELIST = processSelection(inputs)

    ui.messageBox(f"{len(LINELIST)} lines")


def contains(list, item):
    for x in list:
        if x == item:
            return True
    return False


def PT2S(point: adsk.core.Point3D):
    return f"{point.x},{point.y},{point.z}"


def processSelection(inputs: adsk.core.CommandInputs):
    outputList = []
    selector: adsk.core.SelectionCommandInput = inputs.itemById(SELECTOR_ID)
    if selector and selector.selectionCount >= 0:
        originalLine: adsk.fusion.SketchLine = selector.selection(0).entity
        line = originalLine
        outputList = [line]

        #futil.log("Direction 1")
        point = line.endSketchPoint
        while True:
            #futil.log(f"{PT2S(line.startSketchPoint.geometry)} - {PT2S(line.endSketchPoint.geometry)}")
            if point.connectedEntities.count > 2:
                continue

            maybeline = point.connectedEntities.item(0)
            if maybeline == line:
                maybeline = point.connectedEntities.item(1)
            if not maybeline:
                break

            if maybeline.objectType == adsk.fusion.SketchLine.classType():
                if contains(outputList, maybeline):
                    break
                else:
                    outputList.append(maybeline)
                    line = maybeline
                    if point == maybeline.endSketchPoint:
                        point = maybeline.startSketchPoint
                    else:
                        point = maybeline.endSketchPoint

        #futil.log("Direction 2")
        line = originalLine
        point = line.startSketchPoint
        while True:
            #futil.log(f"{PT2S(line.startSketchPoint.geometry)} - {PT2S(line.endSketchPoint.geometry)}")
            if point.connectedEntities.count > 2:
                break
            # futil.log(PT2S(point.geometry))
            maybeline = point.connectedEntities.item(0)
            if maybeline == line:
                maybeline = point.connectedEntities.item(1)
            if not maybeline:
                break

            #futil.log(f"? {PT2S(maybeline.startSketchPoint.geometry)} - {PT2S(maybeline.endSketchPoint.geometry)}")
            if maybeline.objectType == adsk.fusion.SketchLine.classType():
                if contains(outputList, maybeline):
                    break
                else:
                    outputList.insert(0, maybeline)
                    line = maybeline
                    if point == maybeline.endSketchPoint:
                        point = maybeline.startSketchPoint
                    else:
                        point = maybeline.endSketchPoint

    return outputList


def display(points):
    try:
        des = adsk.fusion.Design.cast(app.activeProduct)
        root = des.rootComponent

        global MYGRAPHICS

        # Check to see if a custom graphics groups already exists and delete it.
        if MYGRAPHICS:
            MYGRAPHICS.deleteMe()
            MYGRAPHICS = None
            futil.log('Deleted existing graphics.')
            app.activeViewport.refresh()

        if len(points) > 1:
            # Create a graphics group on the root component.
            MYGRAPHICS = root.customGraphicsGroups.add()

            coordArray = []
            lineArray = []
            curLine = 0
            for point in points:
                coordArray.append(point.x)
                coordArray.append(point.y)
                coordArray.append(point.z)

                lineArray.append(curLine)
                lineArray.append(curLine+1)
                curLine = curLine + 1

            lineArray.pop()
            lineArray.pop()

            coords = adsk.fusion.CustomGraphicsCoordinates.create(coordArray)
            lines = MYGRAPHICS.addLines(coords, lineArray, False)
            lines.weight = 3

            purpleColor = adsk.core.Color.create(255, 0, 128, 100)
            solidColor = adsk.fusion.CustomGraphicsSolidColorEffect.create(
                purpleColor)
            lines.color = solidColor

            # Refresh the graphics.
            app.activeViewport.refresh()
    except:
        futil.handle_error('stop')


def Decimate(inputs: adsk.core.CommandInputs, lines):
    dist: adsk.core.FloatSliderCommandInput = inputs.itemById(DIST_SLIDER_ID)
    mindist = dist.valueOne
    angl: adsk.core.AngleValueCommandInput = inputs.itemById(ANGLE_SLIDER_ID)
    maxAngle = angl.value

    if len(lines) == 1:
        points = [lines[0].startSketchPoint.geometry,
                  lines[0].endSketchPoint.geometry]
        return points

    openEnded = False
    currentPoint: adsk.core.Point3D = lines[0].startSketchPoint.geometry
    if lines[0].endSketchPoint.connectedEntities.count == 1:
        currentPoint = lines[0].endSketchPoint.geometry
        openEnded = True

    if lines[0].startSketchPoint.connectedEntities.count == 1:
        openEnded = True

    points = [currentPoint]

    for x in range(len(lines)):
        line = lines[x]
        futil.log(
            f"L1 {PT2S(line.startSketchPoint.geometry)} - {PT2S(line.endSketchPoint.geometry)}")
        nextLine = line
        if x == len(lines)-1:
            if openEnded:
                nextLine = None
            else:
                nextLine = lines[0]
        else:
            nextLine = lines[x+1]
        point = line.endSketchPoint.geometry
        if point.isEqualTo(currentPoint):
            point = line.startSketchPoint.geometry
        vector = currentPoint.vectorTo(point)

        angleTest = False

        if nextLine:
            futil.log(
                f"L2 {PT2S(nextLine.startSketchPoint.geometry)} - {PT2S(nextLine.endSketchPoint.geometry)}")
            nextPoint = nextLine.endSketchPoint.geometry
            if point.isEqualTo(nextPoint):
                nextPoint = nextLine.startSketchPoint.geometry
            vector2 = currentPoint.vectorTo(nextPoint)
            angle = vector.angleTo(vector2)
            if angle > pi:
                angle = angle - (pi * 2)
            angleTest = abs(angle) < maxAngle

        #futil.log(f"{PT2S(currentPoint)} - {PT2S(nextPoint)}")
        if (not angleTest) or vector.length > mindist:
            currentPoint = point
            points.append(currentPoint)

    return points

# This event handler is called when the command needs to compute a new preview in the graphics window.


def command_preview(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Preview Event')
    inputs = args.command.commandInputs

    global LINELIST
    global DO_RESCAN

    if DO_RESCAN:
        LINELIST = processSelection(inputs)
        DO_RESCAN = False

    points = Decimate(inputs, LINELIST)

    ptcount: adsk.core.StringValueCommandInput = inputs.itemById(PTCOUNT_ID)
    ptcount.value = str(len(points))

    display(points)


# This event handler is called when the user changes anything in the command dialog
# allowing you to modify values of other inputs based on that change.
def command_input_changed(args: adsk.core.InputChangedEventArgs):
    changed_input = args.input
    inputs = args.inputs

    selector: adsk.core.SelectionCommandInput = inputs.itemById(SELECTOR_ID)
    if changed_input == selector:
        global DO_RESCAN
        DO_RESCAN = True

    # General logging for debug.
    futil.log(
        f'{CMD_NAME} Input Changed Event fired from a change to {changed_input.id}')


# This event handler is called when the user interacts with any of the inputs in the dialog
# which allows you to verify that all of the inputs are valid and enables the OK button.
def command_validate_input(args: adsk.core.ValidateInputsEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Validate Input Event')

    inputs = args.inputs
    selector: adsk.core.SelectionCommandInput = inputs.itemById(SELECTOR_ID)

    # Verify the validity of the input values. This controls if the OK button is enabled or not.
    if selector and selector.selectionCount >= 0:
        inputs.areInputsValid = True
    else:
        inputs.areInputsValid = False


# This event handler is called when the command terminates.
def command_destroy(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Destroy Event')

    global local_handlers
    local_handlers = []
