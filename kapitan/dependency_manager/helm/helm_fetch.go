package main

import "C"

import (
	"io/ioutil"
	"os"
	"path/filepath"
	"strings"

	"github.com/otiai10/copy"
	"helm.sh/helm/v3/pkg/action"
	"helm.sh/helm/v3/pkg/cli"
)

//export fetchHelmChart
func fetchHelmChart(c_repoURL, c_chartName, c_chartVersion, c_destinationDir *C.char) *C.char {
	repoURL := C.GoString(c_repoURL)
	chartName := C.GoString(c_chartName)
	chartVersion := C.GoString(c_chartVersion)
	destDir := C.GoString(c_destinationDir)

	client := action.NewPull()

	client.Settings = &cli.EnvSettings{
		Debug:           false,
		RepositoryCache: "/tmp",
	}

	client.ChartPathOptions = action.ChartPathOptions{
		RepoURL: repoURL,
		Verify:  false,
		Version: chartVersion,
	}

	client.UntarDir = destDir
	client.Untar = true

	res, err := client.Run(chartName)
	if err != nil {
		return C.CString(err.Error())
	}

	// remove chart tgz dir
	c, err := ioutil.ReadDir(destDir)
	for _, entry := range c {
		if strings.Contains(entry.Name(), ".tgz") && entry.IsDir() {
			tgzDir := filepath.Join(destDir, entry.Name())
			err = os.Remove(tgzDir)
			if err != nil {
				return C.CString(err.Error())
			}
		}

	}

	// move files from helm client output dir to specified destination dir
	originalDestDir := filepath.Join(destDir, chartName)
	err = copy.Copy(originalDestDir, destDir)
	if err != nil {
		return C.CString(err.Error())
	}

	// remove old originalDestDir
	err = os.RemoveAll(originalDestDir)
	if err != nil {
		return C.CString(err.Error())
	}

	return C.CString(res)
}

// this is required to build this as shared object file using cgo
func main() {}
