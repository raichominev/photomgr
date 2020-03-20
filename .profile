echo "Profile initiation"
echo "$BUILD_PATH"
export LIBRARY_PATH=$BUILD_PATH/exiv2-lx64-0.27.2/lib:$BUILD_PATH/.heroku/boost/lib:$LIBRARY_PATH
export CPATH=$BUILD_PATH/exiv2-lx64-0.27.2/include:$BUILD_PATH/.heroku/boost/include:$CPATH
