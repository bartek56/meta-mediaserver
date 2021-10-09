#!/bin/bash

wget https://github.com/twbs/bootstrap/releases/download/v5.0.0-beta1/bootstrap-5.0.0-beta1-dist.zip
unzip bootstrap-5.0.0-beta1-dist.zip
mv bootstrap-5.0.0-beta1-dist bootstrap-5.0.0
rm bootstrap-5.0.0-beta1-dist.zip

wget https://github.com/twbs/icons/archive/refs/tags/v1.5.0.zip
unzip v1.5.0
mv icons-1.5.0 bootstrap-icons-1.5.0
rm v1.5.0.zip
