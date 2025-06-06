#!/bin/bash

export $(cat .env | sed 's/#.*//g' | xargs) || true
docker build -t awesomecosmonaut/ratings-api-app . || true
docker push awesomecosmonaut/ratings-api-app || true
kubectl delete -f deployment -n hse-coursework-health || true
kubectl apply -f deployment -n hse-coursework-health || true
