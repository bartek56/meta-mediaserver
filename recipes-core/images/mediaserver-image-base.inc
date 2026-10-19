# Package selection is kept in this image include instead of the common image
# class.  The class contains image policy shared by the full MediaServer
# images, while these packagegroups describe the product contents.
IMAGE_INSTALL:append = " \
    packagegroup-mediaserver-network \
    packagegroup-mediaserver-utils \
    packagegroup-mediaserver-audio \
    packagegroup-mediaserver-multimedia \
    packagegroup-mediaserver-services \
    packagegroup-mediaserver-system \
"
