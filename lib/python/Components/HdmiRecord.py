from config import config, ConfigSelection, ConfigSubsection


def InitHdmiRecord():
    config.hdmirecord = ConfigSubsection()

    config.hdmirecord.bitrate = ConfigSelection(
        choices=[
            ("512000", "0.5 Mb/s"),
            ("1024000", "1 Mb/s"),
            ("2048000", "2 Mb/s"),
            ("3072000", "3 Mb/s"),
            ("4096000", "4 Mb/s"),
            ("5120000", "5 Mb/s"),
            ("6144000", "6 Mb/s"),
            ("7168000", "7 Mb/s"),
            ("8192000", "8 Mb/s"),
            ("9216000", "9 Mb/s"),
            ("10240000", "10 Mb/s"),
            ("15360000", "15 Mb/s"),
            ("20480000", "20 Mb/s"),
            ("25600000", "25 Mb/s"),
        ], default="5120000")

    config.hdmirecord.width = ConfigSelection(
        choices=[
            ("180", "180"),      # SD / 4
            ("240", "240"),      # FullHD / 8, SD / 3
            ("320", "320"),      # FullHD / 6
            ("360", "360"),      # SD / 2
            ("384", "384"),      # FullHD / 5
            ("480", "480"),      # FullHD / 4
            ("640", "640"),      # FullHD / 3
            ("720", "720"),      # SD
            ("960", "960"),      # FullHD / 2
            ("1280", "1280"),    # FullHD / 1.5
            ("1920", "1920"),    # FullHD
        ], default="1280")

    config.hdmirecord.height = ConfigSelection(
        choices=[
            ("144", "144"),       # SD / 4
            ("135", "135"),       # FullHD / 8
            ("192", "192"),       # SD / 3
            ("180", "180"),       # FullHD / 6
            ("288", "288"),       # SD / 2
            ("216", "216"),       # FullHD / 5
            ("270", "270"),       # FullHD / 4
            ("360", "360"),       # FullHD / 3
            ("576", "576"),       # SD
            ("540", "540"),       # FullHD / 2
            ("720", "720"),       # FullHD / 1.5
            ("1080", "1080"),     # FullHD
        ], default="720")

    config.hdmirecord.framerate = ConfigSelection(
        choices=[
            ("24000", "24"),
            ("25000", "25"),
            ("30000", "30"),
            ("50000", "50"),
            ("60000", "60"),
        ], default="60000")

    # Intentionally not a boolean because the API expects an integer parsed from the string
    config.hdmirecord.interlaced = ConfigSelection(
        choices=[
            ("0", "No"),
            ("1", "Yes"),
        ], default="0")

    config.hdmirecord.aspectratio = ConfigSelection(
        choices=[
            ("0", "Auto"),
            ("1", "4:3"),
            ("2", "16:9"),
        ], default="0")
