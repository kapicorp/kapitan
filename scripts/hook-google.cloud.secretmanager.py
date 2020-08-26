"""
Acts as a hook for the google-cloud-secret-manager package since PyInstaller
does not natively have a hook for google-cloud-secret-manager
"""
from PyInstaller.utils.hooks import copy_metadata, collect_data_files

datas = copy_metadata("google-cloud-secret-manager")
datas += collect_data_files("grpc")
